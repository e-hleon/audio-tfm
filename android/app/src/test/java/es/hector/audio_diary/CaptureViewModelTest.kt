package es.hector.audio_diary
import java.io.File
import java.time.Instant
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.test.*
import org.junit.*
import org.junit.Assert.*
@OptIn(ExperimentalCoroutinesApi::class)
class CaptureViewModelTest {
 private val dispatcher=StandardTestDispatcher(); @Before fun before(){Dispatchers.setMain(dispatcher)} @After fun after(){Dispatchers.resetMain()}
 @Test fun start_stop_auto_stop_and_cancel()=runTest { val r=FakeAudioRecorder(); val v=CaptureViewModel(r,FakeBackend(),2); v.startRecording();assertTrue(v.state.value is UiState.Recording);v.stopRecording();assertTrue(v.state.value is UiState.Ready);v.startRecording();advanceTimeBy(2000);advanceUntilIdle();assertTrue(v.state.value is UiState.Ready);v.startRecording();val f=r.current.file;v.cancelIfRecording();assertTrue(v.state.value is UiState.Idle);assertFalse(f.exists()) }
 @Test fun recorder_errors_and_discard()=runTest { val a=CaptureViewModel(FakeAudioRecorder(startFails=true),FakeBackend());a.startRecording();assertTrue(a.state.value is UiState.Error); val r=FakeAudioRecorder(stopFails=true);val b=CaptureViewModel(r,FakeBackend());b.startRecording();b.stopRecording();assertTrue(b.state.value is UiState.Error); val ok=FakeAudioRecorder();val c=CaptureViewModel(ok,FakeBackend());c.startRecording();c.stopRecording();val f=ok.current.file;c.discard();assertTrue(c.state.value is UiState.Idle);assertFalse(f.exists()) }
 @Test fun success_new_recording_retry_and_processing_guard()=runTest { val r=FakeAudioRecorder();val b=FakeBackend(failures=1);val v=CaptureViewModel(r,b);v.startRecording();v.stopRecording();val f=r.current.file;v.send("http://t");advanceUntilIdle();assertTrue(v.state.value is UiState.Error);assertTrue(f.exists());v.send("http://t");advanceUntilIdle();assertTrue(v.state.value is UiState.Success);assertFalse(f.exists());v.newRecording();assertTrue(v.state.value is UiState.Idle);v.startRecording();assertTrue(v.state.value is UiState.Recording);assertEquals(2,b.calls) }
 @Test fun security_error_explains_network_permission()=runTest { val v=CaptureViewModel(FakeAudioRecorder(),FakeBackend(failure=SecurityException()));v.startRecording();v.stopRecording();v.send("http://t");advanceUntilIdle();assertEquals("No se puede acceder a la red; comprueba el permiso de Internet",(v.state.value as UiState.Error).message) }
}
class FakeAudioRecorder(private val startFails:Boolean=false,private val stopFails:Boolean=false):AudioRecorder { lateinit var current:CapturedAudio; override fun start():CapturedAudio {if(startFails)error("start");current=CapturedAudio(File.createTempFile("capture-",".m4a").apply{writeBytes(byteArrayOf(1))},Instant.parse("2026-09-05T10:00:00Z"));return current};override fun stop()=if(stopFails)error("stop") else current;override fun discard(){if(::current.isInitialized)current.file.delete()} }
class FakeBackend(private var failures:Int=0,private val failure:Throwable?=null):BackendRepository {var calls=0;override suspend fun process(audio:CapturedAudio,backendUrl:String):ProcessResponse{calls++;failure?.let { throw it };if(failures-->0)throw java.net.ConnectException();return sampleResponse()}}
fun sampleResponse()=ProcessResponse("id","2026-09-05T10:00:00Z","2026-09-05T10:01:00Z",Transcription("hola",model="base"),Analysis("ok",emptyList(),emptyList(),emptyList(),emptyList()))
