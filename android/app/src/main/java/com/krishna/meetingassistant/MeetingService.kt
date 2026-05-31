package com.krishna.meetingassistant

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*

class MeetingService : Service() {

    companion object {
        const val ACTION_START = "ACTION_START"
        const val ACTION_STOP = "ACTION_STOP"
        const val NOTIFICATION_CHANNEL_ID = "meeting_assistant_channel"
        const val NOTIFICATION_ID = 1001
        const val SAMPLE_RATE = 16000
        const val BUFFER_SIZE = 3200  // 100ms at 16kHz, 16-bit mono
    }

    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var webSocketClient: WebSocketClient? = null
    private var sessionId: String = ""

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startMeeting()
            ACTION_STOP -> stopMeeting()
        }
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startMeeting() {
        sessionId = java.util.UUID.randomUUID().toString()
        Log.d("MeetingService", "Starting meeting session: $sessionId")

        // Start foreground service with notification
        val notification = createNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        // Connect WebSocket first
        serviceScope.launch {
            try {
                webSocketClient = WebSocketClient()
                val connected = webSocketClient?.connect(sessionId)
                if (connected == true) {
                    Log.d("MeetingService", "WebSocket connected")
                    startAudioRecording()
                } else {
                    Log.e("MeetingService", "WebSocket connection failed")
                    stopSelf()
                }
            } catch (e: Exception) {
                Log.e("MeetingService", "Connection error: ${e.message}")
                stopSelf()
            }
        }
    }

    private fun stopMeeting() {
        Log.d("MeetingService", "Stopping meeting session: $sessionId")
        isRecording = false

        audioRecord?.let {
            it.stop()
            it.release()
        }
        audioRecord = null

        serviceScope.launch {
            webSocketClient?.disconnect()
            webSocketClient = null
        }

        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun startAudioRecording() {
        val minBufferSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            maxOf(minBufferSize, BUFFER_SIZE * 2)
        )

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            Log.e("MeetingService", "AudioRecord initialization failed")
            stopSelf()
            return
        }

        audioRecord?.startRecording()
        isRecording = true

        serviceScope.launch {
            val buffer = ByteArray(BUFFER_SIZE)
            while (isRecording && isActive) {
                try {
                    val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (read > 0) {
                        // Send audio chunk to WebSocket
                        val chunk = buffer.copyOfRange(0, read)
                        webSocketClient?.sendAudio(chunk)
                    }
                } catch (e: Exception) {
                    Log.e("MeetingService", "Recording error: ${e.message}")
                    break
                }
            }
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIFICATION_CHANNEL_ID,
                "Meeting Assistant",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Listening to meeting audio"
            }
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setContentTitle("Meeting Assistant")
            .setContentText("Listening to meeting audio...")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }
}
