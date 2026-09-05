package es.hector.audio_diary

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import java.time.LocalDate
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay

enum class AppScreen { CAPTURE, HISTORY, DAY }
enum class CaptureMode { MANUAL, CONTINUOUS, SMART }

@Composable fun DiaryApp(capture: CaptureViewModel, backend: BackendRepository, preferences: SharedPreferences) {
    var screen by remember { mutableStateOf(AppScreen.CAPTURE) }; var url by remember { mutableStateOf(preferences.getString("backend_url", "") ?: "") }
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Diario de audio", style = MaterialTheme.typography.headlineMedium); Spacer(Modifier.height(8.dp))
        OutlinedTextField(url, { url = it; preferences.edit().putString("backend_url", it).apply() }, label = { Text("URL del backend") }, modifier = Modifier.fillMaxWidth())
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) { AppScreen.values().forEach { item -> if (screen == item) Button({ screen = item }) { Text(item.name) } else OutlinedButton({ screen = item }) { Text(item.name) } } }
        when (screen) { AppScreen.CAPTURE -> CaptureHome(capture, url, preferences); AppScreen.HISTORY -> HistoryScreen(url, backend); AppScreen.DAY -> DayScreen(url, backend) }
    }
}

@Composable private fun CaptureHome(viewModel: CaptureViewModel, url: String, preferences: SharedPreferences) {
    val context = LocalContext.current; val scope = rememberCoroutineScope(); var mode by remember { mutableStateOf(CaptureMode.MANUAL) }; var active by remember { mutableStateOf(false) }; var enrolling by remember { mutableStateOf(false) }
    var stats by remember { mutableStateOf(CaptureStats.read(context)) }
    LaunchedEffect(active) { while (active) { stats = CaptureStats.read(context); delay(1_000) } }
    val verifier = remember { AcousticSpeakerSimilarity().also { it.load(preferences.getString("speaker_template", "") ?: "") } }; var enrolled by remember { mutableStateOf(verifier.hasEnrollment()) }
    val permissionGranted = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
    var hasPermission by remember { mutableStateOf(permissionGranted) }; val ask = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { hasPermission = it }
    val state by viewModel.state.collectAsStateWithLifecycle(); Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Modo de captura", style = MaterialTheme.typography.titleLarge); Text("Manual: guarda una nota de voz hasta 59 segundos."); Text("Continuo: conserva toda la sesión y la divide en chunks."); Text("Inteligente (experimental): VAD y similitud local pueden omitir o aceptar audio incorrectamente.")
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { CaptureMode.values().forEach { item -> if (mode == item) Button({ mode = item }) { Text(item.name) } else OutlinedButton({ mode = item }) { Text(item.name) } } }
        if (!hasPermission) Button({ ask.launch(Manifest.permission.RECORD_AUDIO) }) { Text("Autorizar micrófono") }
        when (mode) {
            CaptureMode.MANUAL -> ManualCaptureContent(viewModel, url, state, context)
            CaptureMode.CONTINUOUS, CaptureMode.SMART -> { Text(if (mode == CaptureMode.CONTINUOUS) "El modo continuo conserva todo el audio de la sesión hasta procesarlo." else "Experimental: no es reconocimiento infalible.")
                if (mode == CaptureMode.SMART) { Text(if (enrolled) "Plantilla local registrada" else "Sin enrollment: el modo inteligente no puede verificar al usuario"); if (!enrolling) Button({ if (hasPermission) { enrolling = true; scope.launch { runCatching { verifier.enroll(VoiceEnrollmentRecorder(context).record()); preferences.edit().putString("speaker_template", verifier.serialize()).apply(); enrolled = true }; enrolling = false } } }) { Text(if (enrolled) "Reemplazar mi voz" else "Registrar mi voz (4 s)") } else Text("Registrando voz localmente…"); if (enrolled) OutlinedButton({ verifier.clear(); preferences.edit().remove("speaker_template").apply(); enrolled = false }) { Text("Eliminar enrollment") } }
                if (!active) Button({ if (hasPermission) { ContextCompat.startForegroundService(context, Intent(context, CaptureForegroundService::class.java).setAction(CaptureForegroundService.ACTION_START).putExtra(CaptureForegroundService.EXTRA_SMART, mode == CaptureMode.SMART).putExtra(CaptureForegroundService.EXTRA_BACKEND, url)); active = true } }) { Text("Iniciar ${mode.name.lowercase()}") }
                else { Text("Grabando ${mode.name.lowercase()} · micrófono activo", color = MaterialTheme.colorScheme.error); Text(stats); Button({ context.startService(Intent(context, CaptureForegroundService::class.java).setAction(CaptureForegroundService.ACTION_STOP)); active = false }) { Text("Detener") }; Text("Los chunks se suben secuencialmente; un fallo queda pendiente para reintento posterior.") }
            }
        }
    }
}

@Composable private fun ManualCaptureContent(viewModel: CaptureViewModel, url: String, state: UiState, context: Context) {
    when (val current = state) {
        UiState.Idle -> Button({ viewModel.startRecording() }, Modifier.fillMaxWidth()) { Text("Grabar manualmente") }
        is UiState.Recording -> { Text("Grabando · ${current.seconds}s / 59s"); Button(viewModel::stopRecording) { Text("Detener") } }
        is UiState.Ready -> ReadyActions({ viewModel.send(url) }, viewModel::discard)
        is UiState.Processing -> { Text("Procesando audio…"); LinearProgressIndicator(Modifier.fillMaxWidth()) }
        is UiState.Error -> { Text(current.message, color = MaterialTheme.colorScheme.error); if (current.audio != null) ReadyActions({ viewModel.send(url) }, viewModel::discard) else OutlinedButton(viewModel::discard) { Text("Descartar") } }
        is UiState.Success -> { Result(current.response); Button(viewModel::newRecording) { Text("Nueva grabación") } }
    }
}

@Composable private fun HistoryScreen(url: String, backend: BackendRepository) {
    val vm = remember { HistoryViewModel(backend) }; val state by vm.state.collectAsStateWithLifecycle(); Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Button({ vm.load(url) }) { Text("Cargar histórico") }; when (val current = state) { HistoryState.Idle -> Text("Pulsa cargar histórico"); HistoryState.Loading -> LinearProgressIndicator(); is HistoryState.Error -> { Text(current.message); OutlinedButton({ vm.load(url) }) { Text("Reintentar") } }; is HistoryState.Detail -> { Text(current.item.recordedAt); Result(ProcessResponse(current.item.id, current.item.recordedAt, current.item.createdAt, current.item.transcription, current.item.analysis)); OutlinedButton({ vm.load(url) }) { Text("Volver") } }; is HistoryState.Ready -> if (current.items.isEmpty()) Text("No hay interacciones") else current.items.forEach { item -> Text(item.recordedAt); Text(item.analysis.summary); Text(item.analysis.topics.joinToString(", ")); OutlinedButton({ vm.detail(url, item.id) }) { Text("Abrir detalle") }; Spacer(Modifier.height(8.dp)) } }
    }
}

@Composable private fun DayScreen(url: String, backend: BackendRepository) {
    val vm = remember { DayViewModel(backend) }; val state by vm.state.collectAsStateWithLifecycle(); var date by remember { mutableStateOf(LocalDate.now().toString()) }; Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(date, { date = it }, label = { Text("Fecha YYYY-MM-DD") }); Button({ runCatching { vm.load(url, LocalDate.parse(date)) } }) { Text("Cargar día") }; when (val current = state) { DayState.Idle -> Text("Selecciona un día"); DayState.Loading -> LinearProgressIndicator(); is DayState.Error -> { Text(current.message); OutlinedButton({ vm.load(url, LocalDate.parse(date)) }) { Text("Reintentar") } }; is DayState.Ready -> { Text("Interacciones: ${current.value.interactions.size}"); Text("Decisiones"); current.value.decisions.forEach { Text("• ${it.text}") }; Text("Tareas"); current.value.tasks.forEach { Text("• ${it.text}") }; Text("Recordatorios"); current.value.reminders.forEach { Text("• ${it.text}") }; val summary = current.value.summary; if (summary.result != null) { Text("Resumen (${summary.status})"); Text(summary.result.summary); Text(summary.result.topics.joinToString(", ")) } else { Text("Resumen: ${summary.status}") }; if (summary.status == "missing" || summary.status == "stale") Button(vm::generate) { Text(if (summary.status == "missing") "Generar resumen" else "Regenerar resumen") } } }
    }
}
