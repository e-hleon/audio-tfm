package es.hector.audio_diary

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle

class MainActivity : ComponentActivity() {
    private val viewModel by viewModels<CaptureViewModel> { object : ViewModelProvider.Factory { @Suppress("UNCHECKED_CAST") override fun <T : ViewModel> create(modelClass: Class<T>) = CaptureViewModel(MediaRecorderAudioRecorder(this@MainActivity.applicationContext), RetrofitBackendRepository()) as T } }
    override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); clearAbandonedCaptures(cacheDir); setContent { DiaryApp(viewModel, RetrofitBackendRepository(), getSharedPreferences("audio_diary", Context.MODE_PRIVATE)) } }
    override fun onStop() { viewModel.cancelIfRecording(); super.onStop() }
}

@Composable fun AudioDiaryScreen(viewModel: CaptureViewModel, preferences: android.content.SharedPreferences) {
    val state by viewModel.state.collectAsStateWithLifecycle(); var url by remember { mutableStateOf(preferences.getString("backend_url", "") ?: "") }
    val context = androidx.compose.ui.platform.LocalContext.current
    var permissionGranted by remember { mutableStateOf(ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) }
    val requestPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { permissionGranted = it }
    MaterialTheme { Column(Modifier.fillMaxSize().padding(20.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Diario de audio", style = MaterialTheme.typography.headlineMedium)
        OutlinedTextField(value = url, onValueChange = { url = it }, label = { Text("URL del backend") }, modifier = Modifier.fillMaxWidth())
        Text(if (permissionGranted) "Micrófono autorizado" else "Se necesita permiso de micrófono para grabar")
        when (val current = state) {
            UiState.Idle -> Button(onClick = { if (permissionGranted) viewModel.startRecording() else requestPermission.launch(Manifest.permission.RECORD_AUDIO) }, modifier = Modifier.fillMaxWidth()) { Text("Grabar") }
            is UiState.Recording -> { Text("Grabando · ${current.seconds}s / 59s"); Button(onClick = viewModel::stopRecording, modifier = Modifier.fillMaxWidth()) { Text("Detener") } }
            is UiState.Ready -> ReadyActions(onSend = { preferences.edit().putString("backend_url", url).apply(); viewModel.send(url) }, onDiscard = viewModel::discard)
            is UiState.Processing -> { Text("Procesando audio…"); LinearProgressIndicator(Modifier.fillMaxWidth()) }
            is UiState.Error -> { Text(current.message, color = MaterialTheme.colorScheme.error); if (current.audio != null) ReadyActions(onSend = { viewModel.send(url) }, onDiscard = viewModel::discard) else Button(onClick = viewModel::discard) { Text("Descartar") } }
            is UiState.Success -> { Result(current.response); Button(onClick = viewModel::newRecording) { Text("Nueva grabación") } }
        }
    } }
}
@Composable fun ReadyActions(onSend: () -> Unit, onDiscard: () -> Unit) { Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { Button(onClick = onSend, modifier = Modifier.weight(1f)) { Text("Enviar") }; OutlinedButton(onClick = onDiscard, modifier = Modifier.weight(1f)) { Text("Descartar") } } }
@Composable fun Result(response: ProcessResponse) { Text("Procesado", style = MaterialTheme.typography.titleLarge); Text("Resumen: ${response.analysis.summary}"); Text("Transcripción: ${response.transcription.text}"); Text("Temas: ${response.analysis.topics.joinToString()}"); Text("Decisiones: ${response.analysis.decisions.joinToString { it.text }}"); Text("Tareas: ${response.analysis.tasks.joinToString { it.text }}"); Text("Recordatorios: ${response.analysis.reminders.joinToString { it.text }}") }
