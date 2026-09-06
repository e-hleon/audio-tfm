package es.hector.audio_diary

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import java.io.File
import java.time.Instant
import java.util.UUID
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.launch
import kotlinx.coroutines.isActive

/** Servicio visible: captura solo después de una acción explícita del usuario. */
class CaptureForegroundService : Service() {
    companion object {
        const val ACTION_START = "es.hector.audio_diary.START_CAPTURE"
        const val ACTION_STOP = "es.hector.audio_diary.STOP_CAPTURE"
        const val EXTRA_SMART = "smart"
        const val EXTRA_BACKEND = "backend"
        private const val CHANNEL = "capture"
        private const val NOTIFICATION = 42
    }
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var recordingJob: Job? = null
    private var recorder: AudioRecord? = null
    private lateinit var queue: SegmentQueue
    private var smartVerifier: AcousticSpeakerSimilarity? = null
    private val wakeups = Channel<Unit>(Channel.CONFLATED)
    private var uploadCoordinator: SegmentUploadCoordinator? = null
    private var uploadJob: Job? = null
    private var stopRequested = false

    override fun onCreate() {
        super.onCreate(); queue = SegmentQueue(File(cacheDir, "pending-segments"))
        getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel(CHANNEL, "Captura de audio", NotificationManager.IMPORTANCE_LOW))
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) stopCapture()
        else if (recordingJob?.isActive != true) startCapture(intent?.getBooleanExtra(EXTRA_SMART, false) == true, intent?.getStringExtra(EXTRA_BACKEND).orEmpty())
        return START_NOT_STICKY
    }
    private fun startCapture(smart: Boolean, backendUrl: String) {
        stopRequested = false
        if (smart) {
            smartVerifier = AcousticSpeakerSimilarity().also { it.load(getSharedPreferences("audio_diary", MODE_PRIVATE).getString("speaker_template", "") ?: "") }
            if (smartVerifier?.hasEnrollment() != true) { stopSelf(); return }
        }
        val title = if (smart) "Captura inteligente" else "Captura continua"
        val stopIntent = Intent(this, CaptureForegroundService::class.java).setAction(ACTION_STOP)
        val stopPending = PendingIntent.getService(this, 1, stopIntent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now).setContentTitle(title)
            .setContentText("El micrófono está activo").setOngoing(true)
            .addAction(0, "DETENER", stopPending).build()
        if (Build.VERSION.SDK_INT >= 29) startForeground(NOTIFICATION, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE) else startForeground(NOTIFICATION, notification)
        val backend = RetrofitBackendRepository()
        uploadCoordinator = SegmentUploadCoordinator(queue) { item ->
            backend.process(CapturedAudio(item.file, item.recordedAt), backendUrl)
            increment("sent")
        }
        recordingJob = scope.launch { captureLoop(smart) }
        uploadJob = scope.launch { uploadLoop() }
    }
    private suspend fun captureLoop(smart: Boolean) {
        val minimum = AudioRecord.getMinBufferSize(AUDIO_SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (minimum <= 0) { stopSelf(); return }
        val source = AudioRecord(MediaRecorder.AudioSource.MIC, AUDIO_SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(minimum, AUDIO_FRAME_SAMPLES * 2 * 4))
        if (source.state != AudioRecord.STATE_INITIALIZED) { source.release(); stopSelf(); return }
        recorder = source; val audioSource: PcmAudioSource = AndroidAudioRecordSource(source); audioSource.start()
        val maxSamples = AUDIO_SAMPLE_RATE * 30; val readBuffer = ShortArray(AUDIO_FRAME_SAMPLES * 4)
        val accumulated = ArrayList<Short>(); var chunkStart = Instant.now(); val segmenter = if (smart) SmartSegmenter() else null; val framer = PcmFramer()
        try {
            while (recordingJob?.isActive != false) {
                val count = audioSource.read(readBuffer); if (count <= 0) continue
                val samples = readBuffer.copyOf(count)
                if (segmenter != null) for (frame in framer.add(samples)) segmenter.accept(frame)?.let { increment("detected"); if ((smartVerifier?.score(it.samples) ?: 0f) >= .75f) saveSegment(it.samples, it.recordedAt) else increment("discarded") }
                else { accumulated.addAll(samples.toList()); if (accumulated.size >= maxSamples) { saveSegment(accumulated.toShortArray(), chunkStart); accumulated.clear(); chunkStart = Instant.now() } }
            }
        } finally {
            if (segmenter != null) segmenter.stop()?.let { increment("detected"); if ((smartVerifier?.score(it.samples) ?: 0f) >= .75f) saveSegment(it.samples, it.recordedAt) else increment("discarded") }
            else if (accumulated.isNotEmpty()) saveSegment(accumulated.toShortArray(), chunkStart)
            audioSource.stopAndRelease(); recorder = null
        }
    }
    private fun saveSegment(samples: ShortArray, recordedAt: Instant) {
        if (samples.isEmpty()) return
        val directory = File(cacheDir, "pending-segments"); directory.mkdirs(); val file = File(directory, "segment-${recordedAt.toEpochMilli()}-${UUID.randomUUID()}.wav")
        WavWriter.write(file, samples); if (queue.offer(PendingSegment(file, recordedAt))) { increment("enqueued"); wakeups.trySend(Unit) } else { increment("discarded"); file.delete() }
    }
    private suspend fun uploadLoop() {
        wakeups.trySend(Unit)
        while (kotlinx.coroutines.currentCoroutineContext().isActive) {
            wakeups.receive()
            uploadCoordinator?.drain()
            if (stopRequested) return
        }
    }
    private fun increment(key: String) { val prefs = getSharedPreferences("audio_diary", MODE_PRIVATE); prefs.edit().putInt(key, prefs.getInt(key, 0) + 1).apply() }
    private fun stopCapture() {
        if (stopRequested) return
        stopRequested = true
        val activeRecording = recordingJob
        activeRecording?.cancel()
        recorder?.let { runCatching { it.stop(); it.release() }; recorder = null }
        scope.launch {
            activeRecording?.join()
            wakeups.trySend(Unit)
            uploadJob?.join()
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        }
    }
    override fun onDestroy() { recordingJob?.cancel(); recorder?.let { runCatching { it.stop(); it.release() } }; scope.cancel(); super.onDestroy() }
    override fun onBind(intent: Intent?): IBinder? = null
}
