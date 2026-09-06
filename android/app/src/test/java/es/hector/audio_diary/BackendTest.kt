package es.hector.audio_diary

import java.io.File
import java.time.Instant
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test

class BackendTest {
    @Test fun history_groups_only_continuous_chunks_of_the_same_session() {
        val analysis = Analysis("summary", emptyList(), emptyList(), emptyList(), emptyList())
        fun item(id: String, mode: String, session: String?, index: Int?) = InteractionResponse(
            id, "2026-09-05T10:00:00Z", "2026-09-05T10:00:00Z",
            Transcription("text", "es", "base"), analysis, captureMode = mode,
            captureSessionId = session, chunkIndex = index,
        )
        val groups = groupContinuousSessions(listOf(
            item("b", "continuous", "s1", 1), item("a", "continuous", "s1", 0),
            item("c", "continuous", "s2", 0), item("legacy", "manual", null, null),
        ))
        assertEquals(listOf(listOf("a", "b"), listOf("c"), listOf("legacy")), groups.map { it.map(InteractionResponse::id) })
    }
    @Test fun normalizes_valid_url_and_rejects_invalid_one() {
        assertEquals("http://example.test:8000/", normalizeBackendUrl(" http://example.test:8000/ "))
        assertFails { normalizeBackendUrl("example.test") }
    }
    @Test fun process_sends_multipart_with_audio_and_utc_timestamp() = runBlocking {
        val server = MockWebServer(); server.start()
        server.enqueue(MockResponse().setResponseCode(200).setBody(responseJson))
        val file = File.createTempFile("audio", ".m4a").apply { writeBytes(byteArrayOf(1, 2)) }
        val result = RetrofitBackendRepository().process(CapturedAudio(file, Instant.parse("2026-09-05T10:00:00Z"), "continuous", "11111111-1111-1111-1111-111111111111", 2, "22222222-2222-2222-2222-222222222222"), server.url("/").toString())
        val request = server.takeRequest()
        val body = request.body.readUtf8()
        assertEquals("POST", request.method)
        assertEquals("/process", request.path)
        assertTrue(request.getHeader("Content-Type")!!.startsWith("multipart/form-data"))
        assertTrue(body.contains("name=\"file\"")); assertTrue(body.contains(file.name)); assertTrue(body.contains("audio/mp4"))
        assertTrue(body.contains("name=\"recorded_at\"")); assertTrue(body.contains("2026-09-05T10:00:00Z"))
        assertTrue(body.contains("name=\"capture_mode\"")); assertTrue(body.contains("continuous"))
        assertTrue(body.contains("name=\"capture_session_id\"")); assertTrue(body.contains("11111111-1111-1111-1111-111111111111"))
        assertTrue(body.contains("name=\"chunk_index\"")); assertTrue(body.contains("name=\"capture_chunk_id\""))
        assertEquals("id-1", result.interactionId); assertEquals("hola", result.transcription.text)
        assertEquals("d", result.analysis.decisions.single().text); assertEquals("t", result.analysis.tasks.single().text); assertEquals("r", result.analysis.reminders.single().text)
        file.delete(); server.shutdown()
    }
    @Test fun parses_http_errors() = runBlocking {
        val server = MockWebServer(); server.start(); server.enqueue(MockResponse().setResponseCode(500))
        val file = File.createTempFile("audio", ".m4a")
        try { RetrofitBackendRepository().process(CapturedAudio(file, Instant.now()), server.url("/").toString()); fail("Expected failure") } catch (_: Exception) {} finally { file.delete(); server.shutdown() }
    }
    @Test fun reads_health_history_day_and_explicit_summary_endpoints() = runBlocking {
        val server = MockWebServer(); server.start()
        server.enqueue(MockResponse().setBody("{\"status\":\"ready\",\"analysis_configured\":false}"))
        server.enqueue(MockResponse().setBody("[]"))
        server.enqueue(MockResponse().setBody("{\"day\":\"2026-09-05\",\"timezone\":\"UTC\",\"interactions\":[],\"decisions\":[],\"tasks\":[],\"reminders\":[],\"summary\":{\"status\":\"missing\",\"result\":null,\"generated_at\":null,\"model\":null}}"))
        server.enqueue(MockResponse().setBody("{\"status\":\"ready\",\"result\":{\"summary\":\"ok\",\"topics\":[]},\"generated_at\":null,\"model\":\"test\"}"))
        val repo = RetrofitBackendRepository(); val url = server.url("/").toString()
        assertEquals("ready", repo.health(url).status); assertTrue(repo.interactions(url).isEmpty()); assertEquals("missing", repo.day(url, "2026-09-05").summary.status); assertEquals("ready", repo.generateSummary(url, "2026-09-05").status)
        assertEquals("/health", server.takeRequest().path); assertEquals("/interactions?limit=50&offset=0", server.takeRequest().path); assertEquals("/days/2026-09-05", server.takeRequest().path); assertEquals("POST", server.takeRequest().method); server.shutdown()
    }
    private fun assertFails(block: () -> Unit) { try { block(); fail("Expected failure") } catch (_: Exception) {} }
    private val responseJson = """{"interaction_id":"id-1","recorded_at":"2026-09-05T10:00:00Z","created_at":"2026-09-05T10:01:00Z","transcription":{"text":"hola","language":"es","model":"base","device":"cuda","compute_type":"int8_float16"},"analysis":{"summary":"resumen","topics":["tema"],"decisions":[{"text":"d","evidence":"e"}],"tasks":[{"text":"t","assignee":null,"due_date":null,"evidence":"e"}],"reminders":[{"text":"r","when":null,"evidence":"e"}]}}"""
}
