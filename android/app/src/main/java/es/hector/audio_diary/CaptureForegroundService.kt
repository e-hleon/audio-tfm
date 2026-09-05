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
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.launch

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

    override fun onCreate() {
        super.onCreate(); queue = SegmentQueue(File(cacheDir, "pending-segments"))
        getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel(CHANNEL, "Captura de audio", NotificationManager.IMPORTANCE_LOW))
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) stopCapture()
        else if (recordingJob == null) startCapture(intent?.getBooleanExtra(EXTRA_SMART, false) == true, intent?.getStringExtra(EXTRA_BACKEND).orEmpty())
        return START_NOT_STICKY
    }
    private fun startCapture(smart: Boolean, backendUrl: String) {
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
        recordingJob = scope.launch { captureLoop(smart) }
        scope.launch { uploadLoop(backendUrl) }
    }
    private suspend fun captureLoop(smart: Boolean) {
        val minimum = AudioRecord.getMinBufferSize(AUDIO_SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (minimum <= 0) { stopSelf(); return }
        val source = AudioRecord(MediaRecorder.AudioSource.MIC, AUDIO_SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(minimum, AUDIO_FRAME_SAMPLES * 2 * 4))
        recorder = source; val audioSource: PcmAudioSource = AndroidAudioRecordSource(source); audioSource.start()
        val maxSamples = AUDIO_SAMPLE_RATE * 30; val readBuffer = ShortArray(AUDIO_FRAME_SAMPLES * 4)
        val accumulated = ArrayList<Short>(); var chunkStart = Instant.now(); val segmenter = if (smart) SmartSegmenter() else null; val framer = PcmFramer()
        try {
            while (recordingJob?.isActive != false) {
                val count = audioSource.read(readBuffer); if (count <= 0) continue
                val samples = readBuffer.copyOf(count)
                if (segmenter != null) for (frame in framer.add(samples)) segmenter.accept(frame)?.let { if ((smartVerifier?.score(it.samples) ?: 0f) >= .75f) saveSegment(it.samples, it.recordedAt) }
                else { accumulated.addAll(samples.toList()); if (accumulated.size >= maxSamples) { saveSegment(accumulated.toShortArray(), chunkStart); accumulated.clear(); chunkStart = Instant.now() } }
            }
        } finally {
            if (segmenter != null) segmenter.stop()?.let { if ((smartVerifier?.score(it.samples) ?: 0f) >= .75f) saveSegment(it.samples, it.recordedAt) }
            else if (accumulated.isNotEmpty()) saveSegment(accumulated.toShortArray(), chunkStart)
            audioSource.stopAndRelease(); recorder = null
        }
    }
    private fun saveSegment(samples: ShortArray, recordedAt: Instant) {
        val directory = File(cacheDir, "pending-segments"); directory.mkdirs(); val file = File.createTempFile("segment-", ".wav", directory)
        WavWriter.write(file, samples); if (queue.offer(PendingSegment(file, recordedAt))) wakeups.trySend(Unit) else file.delete()
    }
    private suspend fun uploadLoop(backendUrl: String) {
        while (recordingJob?.isActive != false || queue.size > 0) {
            wakeups.receive(); var item = queue.poll()
            while (item != null) {
                try { RetrofitBackendRepository().process(CapturedAudio(item.file, item.recordedAt), backendUrl); item.file.delete() }
                catch (_: Exception) { queue.requeue(item); break }
                item = queue.poll()
            }
        }
    }
    private fun stopCapture() { recordingJob?.cancel(); recordingJob = null; recorder?.let { runCatching { it.stop(); it.release() }; recorder = null }; stopForeground(STOP_FOREGROUND_REMOVE); stopSelf() }
    override fun onDestroy() { recordingJob?.cancel(); recorder?.let { runCatching { it.stop(); it.release() } }; scope.cancel(); super.onDestroy() }
    override fun onBind(intent: Intent?): IBinder? = null
}
