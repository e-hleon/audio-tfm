package es.hector.audio_diary

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.assertIsDisplayed
import org.junit.Rule
import org.junit.Test

/** Smoke instrumentado de la pantalla; no usa micrófono ni backend. */
class ManualCaptureScreenTest {
    @get:Rule val rule = createAndroidComposeRule<ComponentActivity>()
    @Test fun initial_screen_exposes_manual_capture_controls() {
        rule.setContent { AudioDiaryScreen(CaptureViewModel(NoopRecorder(), NoopBackend()), rule.activity.getSharedPreferences("test", 0)) }
        rule.onNodeWithText("Diario de audio").assertIsDisplayed()
        rule.onNodeWithText("Grabar").assertIsDisplayed()
    }
    private class NoopRecorder : AudioRecorder { override fun start(): CapturedAudio = error("not used"); override fun stop(): CapturedAudio = error("not used"); override fun discard() = Unit }
    private class NoopBackend : BackendRepository { override suspend fun process(audio: CapturedAudio, backendUrl: String): ProcessResponse = error("not used") }
}
