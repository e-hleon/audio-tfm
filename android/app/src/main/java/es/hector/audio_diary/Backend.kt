package es.hector.audio_diary

import java.io.File
import java.time.Instant
import java.util.concurrent.TimeUnit
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import retrofit2.http.Multipart
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Part

fun normalizeBackendUrl(value: String): String {
    val trimmed = value.trim().trimEnd('/')
    val parsed = runCatching { java.net.URI(trimmed) }.getOrNull()
    require(parsed?.scheme in setOf("http", "https") && !parsed?.host.isNullOrBlank()) { "URL del backend no válida" }
    return "$trimmed/"
}
interface ProcessApi {
    @Multipart @POST("process") suspend fun process(
        @Part file: MultipartBody.Part,
        @Part("recorded_at") recordedAt: okhttp3.RequestBody,
        @Part("capture_mode") captureMode: okhttp3.RequestBody,
        @Part("capture_session_id") captureSessionId: okhttp3.RequestBody?,
        @Part("chunk_index") chunkIndex: okhttp3.RequestBody?,
        @Part("capture_chunk_id") captureChunkId: okhttp3.RequestBody?,
    ): ProcessResponse
    @GET("health") suspend fun health(): HealthResponse
    @GET("interactions") suspend fun interactions(@Query("limit") limit: Int = 50, @Query("offset") offset: Int = 0): List<InteractionResponse>
    @GET("interactions/{id}") suspend fun interaction(@Path("id") id: String): InteractionResponse
    @GET("days/{day}") suspend fun day(@Path("day") day: String): DayResponse
    @POST("days/{day}/summary") suspend fun generateSummary(@Path("day") day: String): DailySummaryState
}
interface BackendRepository {
    suspend fun process(audio: CapturedAudio, backendUrl: String): ProcessResponse
    suspend fun health(backendUrl: String): HealthResponse = error("Health no implementado")
    suspend fun interactions(backendUrl: String, limit: Int = 50, offset: Int = 0): List<InteractionResponse> = error("Histórico no implementado")
    suspend fun interaction(backendUrl: String, id: String): InteractionResponse = error("Detalle no implementado")
    suspend fun day(backendUrl: String, date: String): DayResponse = error("Día no implementado")
    suspend fun generateSummary(backendUrl: String, date: String): DailySummaryState = error("Resumen no implementado")
}
@OptIn(kotlinx.serialization.ExperimentalSerializationApi::class)
class RetrofitBackendRepository(private val json: Json = Json { ignoreUnknownKeys = false }) : BackendRepository {
    private fun api(backendUrl: String): ProcessApi = Retrofit.Builder().baseUrl(normalizeBackendUrl(backendUrl)).client(OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(180, TimeUnit.SECONDS).writeTimeout(30, TimeUnit.SECONDS).build()).addConverterFactory(json.asConverterFactory("application/json".toMediaType())).build().create(ProcessApi::class.java)
    override suspend fun process(audio: CapturedAudio, backendUrl: String): ProcessResponse {
        require(audio.file.exists()) { "El audio temporal ya no existe" }
        val api = api(backendUrl)
        val mediaType = if (audio.file.extension.equals("wav", ignoreCase = true)) "audio/wav" else "audio/mp4"
        val file = MultipartBody.Part.createFormData("file", audio.file.name, audio.file.asRequestBody(mediaType.toMediaType()))
        fun String.body() = toRequestBody("text/plain".toMediaType())
        return api.process(file, audio.recordedAt.toString().body(), audio.captureMode.body(),
            audio.captureSessionId?.body(), audio.chunkIndex?.toString()?.body(), audio.captureChunkId?.body())
    }
    override suspend fun health(backendUrl: String) = api(backendUrl).health()
    override suspend fun interactions(backendUrl: String, limit: Int, offset: Int) = api(backendUrl).interactions(limit, offset)
    override suspend fun interaction(backendUrl: String, id: String) = api(backendUrl).interaction(id)
    override suspend fun day(backendUrl: String, date: String) = api(backendUrl).day(date)
    override suspend fun generateSummary(backendUrl: String, date: String) = api(backendUrl).generateSummary(date)
}
