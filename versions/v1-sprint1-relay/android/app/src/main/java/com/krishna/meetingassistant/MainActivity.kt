package com.krishna.meetingassistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var ipInput: EditText
    private lateinit var statusText: TextView
    private lateinit var startButton: Button
    private lateinit var stopButton: Button
    private lateinit var testButton: Button

    private var isListening = false
    private var currentIp: String = "178.62.216.144"

    companion object {
        private const val REQUEST_RECORD_AUDIO = 200
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        ipInput = findViewById(R.id.ipInput)
        statusText = findViewById(R.id.statusText)
        startButton = findViewById(R.id.startButton)
        stopButton = findViewById(R.id.stopButton)
        testButton = findViewById(R.id.testButton)

        // Load saved IP or default to server IP
        val prefs = getSharedPreferences("meeting_assistant", MODE_PRIVATE)
        val savedIp = prefs.getString("server_ip", "178.62.216.144")
        ipInput.setText(savedIp)

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

        val ip = ipInput.text.toString().trim()
        if (ip.isEmpty()) {
            updateStatus("Error: Please enter server IP")
            return
        }

        // Save IP to preferences
        getSharedPreferences("meeting_assistant", MODE_PRIVATE)
            .edit()
            .putString("server_ip", ip)
            .apply()

        WebSocketClient.setServerIp(ip)

        val intent = Intent(this, MeetingService::class.java)
        intent.action = MeetingService.ACTION_START
        intent.putExtra("server_ip", ip)
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
        val ip = ipInput.text.toString().trim()
        if (ip.isEmpty()) {
            updateStatus("Error: Please enter server IP")
            return
        }

        WebSocketClient.setServerIp(ip)

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