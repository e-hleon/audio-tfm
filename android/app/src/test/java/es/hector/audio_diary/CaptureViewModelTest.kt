package es.hector.audio_diary

import java.io.File
import java.time.Instant
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.*
import org.junit.Assert.*

@OptIn(ExperimentalCoroutinesApi::class)
class CaptureViewModelTest {
    private val dispatcher = StandardTestDispatcher(); @Before fun setup() { Dispatchers.setMain(dispatcher) }; @After fun down() { Dispatchers.resetMain() }
    @Test fun recording_stops_sends_and_deletes_audio_on_success() = runTest {
        val recorder = FakeRecorder(); val vm = CaptureViewModel(recorder, FakeBackend())
        vm.startRecording(); assertTrue(vm.state.value is UiState.Recording); vm.stopRecording(); assertTrue(vm.state.value is UiState.Ready)
        val audio = (vm.state.value as UiState.Ready).audio.file; vm.send("http://example.test"); advanceUntilIdle()
        assertTrue(vm.state.value is UiState.Success); assertFalse(audio.exists())
    }
    @Test fun failure_keeps_audio_for_manual_retry_and_discard_deletes_it() = runTest {
        val recorder = FakeRecorder(); val vm = CaptureViewModel(recorder, FakeBackend(fail = true)); vm.startRecording(); vm.stopRecording(); val file = (vm.state.value as UiState.Ready).audio.file
        vm.send("http://example.test"); advanceUntilIdle(); assertTrue(vm.state.value is UiState.Error); assertTrue(file.exists()); vm.discard(); assertTrue(vm.state.value is UiState.Idle); assertFalse(file.exists())
    }
    private class FakeRecorder : AudioRecorder { private var audio: CapturedAudio? = null; override fun start() = CapturedAudio(File.createTempFile("fake", ".m4a").also { it.writeBytes(byteArrayOf(1)) }, Instant.parse("2026-09-05T10:00:00Z")).also { audio = it }; override fun stop() = checkNotNull(audio); override fun discard() { audio?.file?.delete() } }
    private class FakeBackend(private val fail: Boolean = false) : BackendRepository { override suspend fun process(audio: CapturedAudio, backendUrl: String): ProcessResponse { if (fail) throw java.net.ConnectException(); return ProcessResponse("id", "2026-09-05T10:00:00Z", "2026-09-05T10:01:00Z", Transcription("hola", model = "base"), Analysis("ok", emptyList(), emptyList(), emptyList(), emptyList())) } }
}
