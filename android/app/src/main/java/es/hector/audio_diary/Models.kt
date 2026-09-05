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
