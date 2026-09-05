package es.hector.audio_diary

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import java.io.File
import java.io.FileOutputStream
import java.time.Instant
import kotlin.math.log10
import kotlin.math.sqrt
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

const val AUDIO_SAMPLE_RATE = 16_000
const val AUDIO_FRAME_MILLIS = 20
const val AUDIO_FRAME_SAMPLES = AUDIO_SAMPLE_RATE * AUDIO_FRAME_MILLIS / 1_000
object CaptureStats {
    fun read(context: Context): String { val p = context.getSharedPreferences("audio_diary", Context.MODE_PRIVATE); return "Detectados ${p.getInt("detected", 0)} · enviados ${p.getInt("sent", 0)} · descartados ${p.getInt("discarded", 0)}" }
}

interface PcmAudioSource { fun start(); fun read(buffer: ShortArray): Int; fun stopAndRelease() }
class AndroidAudioRecordSource(private val record: AudioRecord) : PcmAudioSource {
    override fun start() = record.startRecording()
    override fun read(buffer: ShortArray) = record.read(buffer, 0, buffer.size)
    override fun stopAndRelease() { runCatching { record.stop() }; record.release() }
}

/** Ring buffer de tamaño fijo: conserva únicamente el audio inmediatamente anterior. */
class PcmRingBuffer(private val capacity: Int) {
    private val values = ShortArray(capacity)
    private var next = 0
    private var count = 0
    fun add(samples: ShortArray) { samples.forEach { values[next] = it; next = (next + 1) % capacity; count = minOf(count + 1, capacity) } }
    fun snapshot(): ShortArray = ShortArray(count) { index -> values[(next - count + index + capacity) % capacity] }
    val size: Int get() = count
}

class PcmFramer(private val frameSamples: Int = AUDIO_FRAME_SAMPLES) {
    private val pending = ArrayList<Short>()
    fun add(samples: ShortArray): List<ShortArray> {
        pending.ensureCapacity(pending.size + samples.size)
        samples.forEach { pending.add(it) }
        val frames = mutableListOf<ShortArray>()
        while (pending.size >= frameSamples) {
            frames += pending.take(frameSamples).toShortArray()
            repeat(frameSamples) { pending.removeAt(0) }
        }
        return frames
    }
}

/** Baseline VAD energético adaptativo; no es un modelo de aprendizaje automático. */
class EnergyVad(
    private val initialNoiseDb: Double = -55.0,
    private val marginDb: Double = 10.0,
    private val hysteresisDb: Double = 3.0
) {
    private var noiseDb = initialNoiseDb
    fun energyDb(frame: ShortArray): Double {
        val rms = sqrt(frame.map { it.toDouble() * it }.average()) / Short.MAX_VALUE
        return 20.0 * log10(maxOf(rms, 1e-8))
    }
    fun isSpeech(frame: ShortArray, previousSpeech: Boolean = false): Boolean {
        val current = energyDb(frame)
        if (current < noiseDb + marginDb) noiseDb = noiseDb * .98 + current * .02
        return current >= noiseDb + marginDb - if (previousSpeech) hysteresisDb else 0.0
    }
}

/** Plantilla acústica experimental: características simples y similitud coseno, no biometría. */
class AcousticSpeakerSimilarity(private var template: FloatArray? = null) {
    fun representation(samples: ShortArray): FloatArray {
        if (samples.isEmpty()) return floatArrayOf(0f, 0f, 0f)
        val mean = samples.map { it.toDouble() }.average()
        val centered = samples.map { it - mean }
        val energy = sqrt(centered.map { it * it }.average()).toFloat()
        val crossings = centered.zipWithNext().count { (a, b) -> (a >= 0) != (b >= 0) }.toFloat() / samples.size
        return floatArrayOf(mean.toFloat(), energy, crossings)
    }
    fun enroll(samples: ShortArray) { template = representation(samples) }
    fun enrollRepresentation(values: FloatArray) { require(values.size == 3); template = values }
    fun hasEnrollment() = template != null
    fun score(samples: ShortArray): Float {
        val expected = template ?: return 0f
        val actual = representation(samples)
        val dot = expected.zip(actual).sumOf { (a, b) -> (a * b).toDouble() }
        val a = sqrt(expected.sumOf { (it * it).toDouble() }); val b = sqrt(actual.sumOf { (it * it).toDouble() })
        return if (a == 0.0 || b == 0.0) 0f else (dot / (a * b)).toFloat()
    }
    fun serialize(): String = template?.joinToString(",") ?: ""
    fun load(serialized: String) { template = serialized.split(",").filter { it.isNotBlank() }.map { it.toFloat() }.toFloatArray().takeIf { it.size == 3 } }
    fun clear() { template = null }
}

/** Enrollment explícito: solo conserva tres números acústicos en preferencias privadas. */
class VoiceEnrollmentRecorder(private val context: Context) {
    suspend fun record(seconds: Int = 4): FloatArray = withContext(Dispatchers.IO) {
        val minimum = AudioRecord.getMinBufferSize(AUDIO_SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        require(minimum > 0) { "El dispositivo no admite PCM mono a 16 kHz" }
        val source = AudioRecord(MediaRecorder.AudioSource.MIC, AUDIO_SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(minimum, AUDIO_FRAME_SAMPLES * 4))
        val samples = ShortArray(AUDIO_SAMPLE_RATE * seconds); var offset = 0; val read = ShortArray(AUDIO_FRAME_SAMPLES * 4)
        try { source.startRecording(); while (offset < samples.size) { val count = source.read(read, 0, minOf(read.size, samples.size - offset)); if (count > 0) { read.copyInto(samples, offset, 0, count); offset += count } } }
        finally { runCatching { source.stop() }; source.release() }
        AcousticSpeakerSimilarity().representation(samples)
    }
}

data class PendingSegment(val file: File, val recordedAt: Instant)
class SegmentQueue(private val directory: File, private val maxSegments: Int = 20) {
    private val pending = ArrayDeque<PendingSegment>()
    init {
        directory.mkdirs()
        directory.listFiles { file -> file.name.startsWith("segment-") && file.extension == "wav" }
            ?.sortedBy { it.name }?.forEachIndexed { index, file -> if (index < maxSegments) pending.addLast(PendingSegment(file, Instant.now())) else file.delete() }
    }
    @Synchronized fun offer(segment: PendingSegment): Boolean { if (pending.size >= maxSegments) return false; pending.addLast(segment); return true }
    @Synchronized fun poll(): PendingSegment? = pending.removeFirstOrNull()
    @Synchronized fun requeue(segment: PendingSegment) { if (pending.size < maxSegments) pending.addFirst(segment) }
    @get:Synchronized val size: Int get() = pending.size
    val capacity: Int get() = maxSegments
}

object WavWriter {
    fun write(file: File, samples: ShortArray, sampleRate: Int = AUDIO_SAMPLE_RATE) {
        FileOutputStream(file).use { out ->
            val dataSize = samples.size * 2
            fun ascii(value: String) = value.toByteArray(Charsets.US_ASCII).also { out.write(it) }
            fun le(value: Int) { out.write(value and 255); out.write(value shr 8 and 255); out.write(value shr 16 and 255); out.write(value shr 24 and 255) }
            fun leShort(value: Int) { out.write(value and 255); out.write(value shr 8 and 255) }
            ascii("RIFF"); le(36 + dataSize); ascii("WAVE"); ascii("fmt "); le(16); leShort(1); leShort(1); le(sampleRate); le(sampleRate * 2); leShort(2); leShort(16); ascii("data"); le(dataSize)
            samples.forEach { leShort(it.toInt()) }
        }
    }
}

enum class SmartState { SILENCE, POSSIBLE_SPEECH, SPEECH, ENDING }
data class SmartSegment(val samples: ShortArray, val recordedAt: Instant)
class SmartSegmenter(
    private val vad: EnergyVad = EnergyVad(), private val preRollFrames: Int = 50,
    private val minimumSpeechFrames: Int = 3, private val endingSilenceFrames: Int = 40,
    private val maximumFrames: Int = 2_250, private val clock: () -> Instant = { Instant.now() }
) {
    private val preRoll = PcmRingBuffer(preRollFrames * AUDIO_FRAME_SAMPLES)
    private val current = ArrayList<Short>(); private var speechFrames = 0; private var silentFrames = 0; private var segmentStart: Instant? = null
    var state = SmartState.SILENCE; private set
    fun accept(frame: ShortArray): SmartSegment? {
        val speech = vad.isSpeech(frame, state == SmartState.SPEECH || state == SmartState.ENDING)
        if (state == SmartState.SILENCE) { preRoll.add(frame); if (speech) { state = SmartState.POSSIBLE_SPEECH; segmentStart = clock(); current.addAll(preRoll.snapshot().toList()); speechFrames = 1 } }
        else { current.addAll(frame.toList()); if (speech) { speechFrames++; silentFrames = 0; state = SmartState.SPEECH } else if (state == SmartState.SPEECH) { silentFrames++; state = SmartState.ENDING } }
        val close = (state == SmartState.ENDING && silentFrames >= endingSilenceFrames && speechFrames >= minimumSpeechFrames) || current.size >= maximumFrames * AUDIO_FRAME_SAMPLES
        if (close) return finish()
        return null
    }
    fun stop(): SmartSegment? = if (current.isNotEmpty() && speechFrames >= minimumSpeechFrames) finish() else { current.clear(); state = SmartState.SILENCE; null }
    private fun finish(): SmartSegment { val result = SmartSegment(current.toShortArray(), segmentStart ?: clock()); current.clear(); speechFrames = 0; silentFrames = 0; segmentStart = null; state = SmartState.SILENCE; return result }
}
