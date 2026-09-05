package es.hector.audio_diary

import java.io.File
import java.time.Instant
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

data class CapturedAudio(val file: File, val recordedAt: Instant)

@Serializable data class ProcessResponse(
    @SerialName("interaction_id") val interactionId: String,
    @SerialName("recorded_at") val recordedAt: String,
    @SerialName("created_at") val createdAt: String,
    val transcription: Transcription, val analysis: Analysis
)
@Serializable data class Transcription(val text: String, val language: String? = null, val model: String, val device: String? = null, @SerialName("compute_type") val computeType: String? = null)
@Serializable data class Analysis(val summary: String, val topics: List<String>, val decisions: List<Decision>, val tasks: List<Task>, val reminders: List<Reminder>)
@Serializable data class Decision(val text: String, val evidence: String)
@Serializable data class Task(val text: String, val assignee: String? = null, @SerialName("due_date") val dueDate: String? = null, val evidence: String)
@Serializable data class Reminder(val text: String, @SerialName("when") val whenText: String? = null, val evidence: String)

@Serializable data class InteractionResponse(
    val id: String, @SerialName("recorded_at") val recordedAt: String,
    @SerialName("created_at") val createdAt: String, val transcription: Transcription,
    val analysis: Analysis, @SerialName("analysis_model") val analysisModel: String? = null
)
@Serializable data class DailySummaryState(
    val status: String, val result: DailySummaryResult? = null,
    @SerialName("generated_at") val generatedAt: String? = null, val model: String? = null
)
@Serializable data class DailySummaryResult(val summary: String, val topics: List<String>)
@Serializable data class DayResponse(
    val day: String, val timezone: String, val interactions: List<InteractionResponse>,
    val decisions: List<Decision>, val tasks: List<Task>, val reminders: List<Reminder>,
    val summary: DailySummaryState
)
@Serializable data class HealthResponse(val status: String, @SerialName("analysis_configured") val analysisConfigured: Boolean = false, val model: String? = null)
