package es.hector.audio_diary

import android.content.Context
import android.media.MediaRecorder
import java.io.File
import java.time.Clock
import java.time.Instant

interface AudioRecorder { fun start(): CapturedAudio; fun stop(): CapturedAudio; fun discard() }

fun clearAbandonedCaptures(cacheDir: File) {
    cacheDir.listFiles { file -> file.name.startsWith("capture-") && file.name.endsWith(".m4a") }
        ?.forEach { it.delete() }
}

class MediaRecorderAudioRecorder(private val context: Context, private val clock: Clock = Clock.systemUTC()) : AudioRecorder {
    private var recorder: MediaRecorder? = null
    private var captured: CapturedAudio? = null
    override fun start(): CapturedAudio {
        check(recorder == null) { "Ya hay una grabación activa" }
        val file = File.createTempFile("capture-", ".m4a", context.cacheDir)
        try {
            val media = MediaRecorder().apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setOutputFile(file.absolutePath); prepare(); start()
            }
            return CapturedAudio(file, Instant.now(clock)).also { captured = it; recorder = media }
        } catch (error: Exception) { file.delete(); throw error }
    }
    override fun stop(): CapturedAudio {
        val current = checkNotNull(captured) { "No hay grabación activa" }
        try { recorder?.stop() } finally { recorder?.release(); recorder = null; captured = null }
        return current
    }
    override fun discard() { runCatching { recorder?.stop() }; recorder?.release(); recorder = null; captured?.file?.delete(); captured = null }
}
