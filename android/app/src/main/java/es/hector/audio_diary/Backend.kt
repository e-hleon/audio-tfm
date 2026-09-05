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
import retrofit2.http.POST
import retrofit2.http.Part

fun normalizeBackendUrl(value: String): String {
    val trimmed = value.trim().trimEnd('/')
    val parsed = runCatching { java.net.URI(trimmed) }.getOrNull()
    require(parsed?.scheme in setOf("http", "https") && !parsed?.host.isNullOrBlank()) { "URL del backend no válida" }
    return "$trimmed/"
}
interface ProcessApi { @Multipart @POST("process") suspend fun process(@Part file: MultipartBody.Part, @Part("recorded_at") recordedAt: okhttp3.RequestBody): ProcessResponse }
interface BackendRepository { suspend fun process(audio: CapturedAudio, backendUrl: String): ProcessResponse }
@OptIn(kotlinx.serialization.ExperimentalSerializationApi::class)
class RetrofitBackendRepository(private val json: Json = Json { ignoreUnknownKeys = false }) : BackendRepository {
    override suspend fun process(audio: CapturedAudio, backendUrl: String): ProcessResponse {
        require(audio.file.exists()) { "El audio temporal ya no existe" }
        val api = Retrofit.Builder().baseUrl(normalizeBackendUrl(backendUrl)).client(OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(180, TimeUnit.SECONDS).writeTimeout(30, TimeUnit.SECONDS).build()).addConverterFactory(json.asConverterFactory("application/json".toMediaType())).build().create(ProcessApi::class.java)
        val file = MultipartBody.Part.createFormData("file", audio.file.name, audio.file.asRequestBody("audio/mp4".toMediaType()))
        return api.process(file, audio.recordedAt.toString().toRequestBody("text/plain".toMediaType()))
    }
}
