package es.hector.audio_diary

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface HistoryState { data object Idle : HistoryState; data object Loading : HistoryState; data class Ready(val items: List<InteractionResponse>) : HistoryState; data class Detail(val item: InteractionResponse) : HistoryState; data class Error(val message: String) : HistoryState }
fun groupContinuousSessions(items: List<InteractionResponse>): List<List<InteractionResponse>> {
    val groups = linkedMapOf<String, MutableList<InteractionResponse>>()
    items.sortedByDescending { it.recordedAt }.forEach { item ->
        val key = if (item.captureMode == "continuous" && item.captureSessionId != null) {
            "continuous:${item.captureSessionId}"
        } else "interaction:${item.id}"
        groups.getOrPut(key) { mutableListOf() }.add(item)
    }
    return groups.values.map { group -> group.sortedWith(compareBy<InteractionResponse> { it.chunkIndex ?: Int.MAX_VALUE }.thenBy { it.recordedAt }) }
}
class HistoryViewModel(private val backend: BackendRepository) : ViewModel() {
    private val mutable = MutableStateFlow<HistoryState>(HistoryState.Idle); val state: StateFlow<HistoryState> = mutable.asStateFlow()
    fun load(url: String) { mutable.value = HistoryState.Loading; viewModelScope.launch { runCatching { backend.interactions(url) }.onSuccess { mutable.value = HistoryState.Ready(it.sortedByDescending { item -> item.recordedAt }) }.onFailure { mutable.value = HistoryState.Error(errorMessage(it)) } } }
    fun detail(url: String, id: String) { mutable.value = HistoryState.Loading; viewModelScope.launch { runCatching { backend.interaction(url, id) }.onSuccess { mutable.value = HistoryState.Detail(it) }.onFailure { mutable.value = HistoryState.Error("No se pudo cargar el detalle") } } }
    private fun errorMessage(error: Throwable) = if (error is java.net.ConnectException) "No se puede conectar con el servidor" else "No se pudo cargar el histórico"
}

sealed interface DayState { data object Idle : DayState; data object Loading : DayState; data class Ready(val value: DayResponse) : DayState; data class Error(val message: String) : DayState }
class DayViewModel(private val backend: BackendRepository) : ViewModel() {
    private val mutable = MutableStateFlow<DayState>(DayState.Idle); val state: StateFlow<DayState> = mutable.asStateFlow(); var selectedDate: LocalDate = LocalDate.now(); private var url = ""
    fun load(url: String, date: LocalDate = selectedDate) { this.url = url; selectedDate = date; mutable.value = DayState.Loading; viewModelScope.launch { runCatching { backend.day(url, date.toString()) }.onSuccess { mutable.value = DayState.Ready(it) }.onFailure { mutable.value = DayState.Error("No se pudo cargar el día") } } }
    fun generate() { if (url.isBlank()) return; mutable.value = DayState.Loading; viewModelScope.launch { runCatching { backend.generateSummary(url, selectedDate.toString()); backend.day(url, selectedDate.toString()) }.onSuccess { mutable.value = DayState.Ready(it) }.onFailure { mutable.value = DayState.Error("No se pudo generar el resumen") } } }
}
