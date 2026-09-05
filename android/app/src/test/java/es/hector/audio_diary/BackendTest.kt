package es.hector.audio_diary

import java.io.File
import java.time.Instant
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test

class BackendTest {
    @Test fun normalizes_valid_url_and_rejects_invalid_one() {
        assertEquals("http://example.test:8000/", normalizeBackendUrl(" http://example.test:8000/ "))
        assertFails { normalizeBackendUrl("example.test") }
    }
    @Test fun process_sends_multipart_with_audio_and_utc_timestamp() = runBlocking {
        val server = MockWebServer(); server.start()
        server.enqueue(MockResponse().setResponseCode(200).setBody(responseJson))
        val file = File.createTempFile("audio", ".m4a").apply { writeBytes(byteArrayOf(1, 2)) }
        val result = RetrofitBackendRepository().process(CapturedAudio(file, Instant.parse("2026-09-05T10:00:00Z")), server.url("/").toString())
        val request = server.takeRequest()
        val body = request.body.readUtf8()
        assertEquals("POST", request.method)
        assertEquals("/process", request.path)
        assertTrue(request.getHeader("Content-Type")!!.startsWith("multipart/form-data"))
        assertTrue(body.contains("name=\"file\"")); assertTrue(body.contains(file.name)); assertTrue(body.contains("audio/mp4"))
        assertTrue(body.contains("name=\"recorded_at\"")); assertTrue(body.contains("2026-09-05T10:00:00Z"))
        assertEquals("id-1", result.interactionId); assertEquals("hola", result.transcription.text)
        assertEquals("d", result.analysis.decisions.single().text); assertEquals("t", result.analysis.tasks.single().text); assertEquals("r", result.analysis.reminders.single().text)
        file.delete(); server.shutdown()
    }
    @Test fun parses_http_errors() = runBlocking {
        val server = MockWebServer(); server.start(); server.enqueue(MockResponse().setResponseCode(500))
        val file = File.createTempFile("audio", ".m4a")
        try { RetrofitBackendRepository().process(CapturedAudio(file, Instant.now()), server.url("/").toString()); fail("Expected failure") } catch (_: Exception) {} finally { file.delete(); server.shutdown() }
    }
    private fun assertFails(block: () -> Unit) { try { block(); fail("Expected failure") } catch (_: Exception) {} }
    private val responseJson = """{"interaction_id":"id-1","recorded_at":"2026-09-05T10:00:00Z","created_at":"2026-09-05T10:01:00Z","transcription":{"text":"hola","language":"es","model":"base","device":"cuda","compute_type":"int8_float16"},"analysis":{"summary":"resumen","topics":["tema"],"decisions":[{"text":"d","evidence":"e"}],"tasks":[{"text":"t","assignee":null,"due_date":null,"evidence":"e"}],"reminders":[{"text":"r","when":null,"evidence":"e"}]}}"""
}
