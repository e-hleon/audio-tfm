package es.hector.audio_diary

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.time.Instant
import org.junit.Assert.*
import org.junit.Test

class SmartAudioTest {
    @Test fun ring_buffer_wraps_and_keeps_recent_order() {
        val ring = PcmRingBuffer(4); ring.add(shortArrayOf(1, 2, 3)); ring.add(shortArrayOf(4, 5))
        assertArrayEquals(shortArrayOf(2, 3, 4, 5), ring.snapshot())
    }
    @Test fun wav_has_pcm16_mono_header_and_sizes() {
        val file = File.createTempFile("audio-test", ".wav")
        try { WavWriter.write(file, shortArrayOf(1, -2, 3), 16_000); val bytes = file.readBytes()
            assertEquals("RIFF", String(bytes, 0, 4)); assertEquals("WAVE", String(bytes, 8, 4)); assertEquals("data", String(bytes, 36, 4))
            assertEquals(42, ByteBuffer.wrap(bytes, 4, 4).order(ByteOrder.LITTLE_ENDIAN).int); assertEquals(6, ByteBuffer.wrap(bytes, 40, 4).order(ByteOrder.LITTLE_ENDIAN).int)
        } finally { file.delete() }
    }
    @Test fun energy_vad_rejects_silence_and_accepts_signal() {
        val vad = EnergyVad(); assertFalse(vad.isSpeech(ShortArray(AUDIO_FRAME_SAMPLES))); assertTrue(vad.isSpeech(ShortArray(AUDIO_FRAME_SAMPLES) { 10_000 }))
    }
    @Test fun framer_turns_partial_reads_into_fixed_frames() {
        val framer = PcmFramer(4); assertTrue(framer.add(shortArrayOf(1, 2)).isEmpty()); val frames = framer.add(shortArrayOf(3, 4, 5, 6))
        assertEquals(1, frames.size); assertArrayEquals(shortArrayOf(1, 2, 3, 4), frames.single()); assertTrue(framer.add(shortArrayOf(7)).isEmpty())
    }
    @Test fun speaker_template_scores_same_features_and_can_be_removed() {
        val verifier = AcousticSpeakerSimilarity(); val sample = ShortArray(1_000) { if (it % 2 == 0) 1000 else -1000 }
        verifier.enroll(sample); assertTrue(verifier.hasEnrollment()); assertTrue(verifier.score(sample) > .99f); verifier.clear(); assertFalse(verifier.hasEnrollment())
    }
    @Test fun queue_rejects_beyond_capacity_and_requeues_failures() {
        val queue = SegmentQueue(createTempDir("queue"), 1); val first = PendingSegment(File.createTempFile("one", ".wav"), Instant.EPOCH); val second = PendingSegment(File.createTempFile("two", ".wav"), Instant.EPOCH)
        assertTrue(queue.offer(first)); assertFalse(queue.offer(second)); assertEquals(first, queue.poll()); queue.requeue(first); assertEquals(1, queue.size); first.file.delete(); second.file.delete()
    }
    @Test fun segmenter_includes_preroll_and_closes_after_silence() {
        val segmenter = SmartSegmenter(preRollFrames = 2, minimumSpeechFrames = 1, endingSilenceFrames = 2, clock = { Instant.EPOCH })
        val silent = ShortArray(AUDIO_FRAME_SAMPLES); val voice = ShortArray(AUDIO_FRAME_SAMPLES) { 10_000 }
        segmenter.accept(silent); segmenter.accept(silent); segmenter.accept(voice); segmenter.accept(silent)
        val result = segmenter.accept(silent); assertNotNull(result); assertTrue(result!!.samples.size >= AUDIO_FRAME_SAMPLES * 3); assertEquals(Instant.EPOCH, result.recordedAt)
    }
}
