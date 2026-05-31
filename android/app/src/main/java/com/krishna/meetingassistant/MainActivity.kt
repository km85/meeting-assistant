package com.krishna.meetingassistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var startButton: Button
    private lateinit var stopButton: Button
    private lateinit var testButton: Button

    private var isListening = false

    companion object {
        private const val REQUEST_RECORD_AUDIO = 200
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        startButton = findViewById(R.id.startButton)
        stopButton = findViewById(R.id.stopButton)
        testButton = findViewById(R.id.testButton)

        startButton.setOnClickListener { startListening() }
        stopButton.setOnClickListener { stopListening() }
        testButton.setOnClickListener { testConnection() }

        updateStatus("Not listening")
    }

    private fun startListening() {
        if (!hasAudioPermission()) {
            requestAudioPermission()
            return
        }

        val intent = Intent(this, MeetingService::class.java)
        intent.action = MeetingService.ACTION_START
        ContextCompat.startForegroundService(this, intent)

        isListening = true
        updateStatus("Listening...")
        startButton.isEnabled = false
        stopButton.isEnabled = true
    }

    private fun stopListening() {
        val intent = Intent(this, MeetingService::class.java)
        intent.action = MeetingService.ACTION_STOP
        startService(intent)

        isListening = false
        updateStatus("Not listening")
        startButton.isEnabled = true
        stopButton.isEnabled = false
    }

    private fun testConnection() {
        lifecycleScope.launch {
            try {
                val result = WebSocketClient.testConnection()
                updateStatus("Connected: $result")
            } catch (e: Exception) {
                updateStatus("Error: ${e.message}")
            }
        }
    }

    private fun updateStatus(status: String) {
        statusText.text = "Status: $status"
    }

    private fun hasAudioPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this, Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun requestAudioPermission() {
        ActivityCompat.requestPermissions(
            this,
            arrayOf(Manifest.permission.RECORD_AUDIO),
            REQUEST_RECORD_AUDIO
        )
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_RECORD_AUDIO && grantResults.isNotEmpty()
            && grantResults[0] == PackageManager.PERMISSION_GRANTED
        ) {
            startListening()
        } else {
            updateStatus("Permission denied")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isListening) {
            stopListening()
        }
    }
}