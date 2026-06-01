package com.krishna.meetingassistant

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import android.util.Log
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.WebSocket
import java.security.KeyStore
import java.util.concurrent.TimeUnit
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class WebSocketClient {

    companion object {
        private const val TAG = "WebSocketClient"
        private const val BACKEND_URL = "ws://YOUR_SERVER_IP:8000/audio-stream"  // Ganti dengan IP server kamu
        private const val HEALTH_URL = "http://YOUR_SERVER_IP:8000/health"  // Health check URL
        private const val PREFS_NAME = "meeting_assistant_prefs"
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val KEY_ALIAS = "backend_auth_token_key"
        private const val IV_PREF_KEY = "auth_token_iv"
        private const val ENCRYPTED_TOKEN_KEY = "auth_token_encrypted"

        suspend fun testConnection(): String {
            return try {
                val client = OkHttpClient.Builder()
                    .connectTimeout(5, TimeUnit.SECONDS)
                    .build()
                val request = Request.Builder()
                    .url("http://YOUR_SERVER_IP:8000/health")
                    .build()
                val response = client.newCall(request).execute()
                if (response.isSuccessful) {
                    "OK - Backend reachable"
                } else {
                    "Error: ${response.code}"
                }
            } catch (e: Exception) {
                "Error: ${e.message}"
            }
        }
    }

    private var webSocket: WebSocket? = null
    private var client: OkHttpClient? = null
    private var isConnected = false
    private val clientScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun connect(sessionId: String): Boolean {
        return try {
            val authToken = getAuthToken() ?: return false

            client = OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .pingInterval(20, TimeUnit.SECONDS)
                .build()

            val request = Request.Builder()
                .url(BACKEND_URL)
                .addHeader("Authorization", "Bearer $authToken")
                .addHeader("X-Session-ID", sessionId)
                .build()

            val listener = object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    Log.d(TAG, "WebSocket opened")
                    isConnected = true

                    // Send initial metadata
                    val metadata = """
                        {
                            "session_id": "$sessionId",
                            "device": "android",
                            "timestamp": ${System.currentTimeMillis()}
                        }
                    """.trimIndent()
                    webSocket.send(metadata)
                }

                override fun onMessage(webSocket: WebSocket, text: String) {
                    Log.d(TAG, "Received: $text")
                    when {
                        text.contains("connected") -> Log.d(TAG, "Server confirmed connection")
                        text.contains("error") -> Log.e(TAG, "Server error: $text")
                    }
                }

                override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                    Log.d(TAG, "WebSocket closing: $code - $reason")
                    isConnected = false
                }

                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                    Log.d(TAG, "WebSocket closed: $code - $reason")
                    isConnected = false
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    Log.e(TAG, "WebSocket failure: ${t.message}")
                    isConnected = false
                    clientScope.launch {
                        delay(5000)
                        connect(sessionId)
                    }
                }
            }

            webSocket = client?.newWebSocket(request, listener)
            true
        } catch (e: Exception) {
            Log.e(TAG, "Connection error: ${e.message}")
            false
        }
    }

    fun sendAudio(audioChunk: ByteArray) {
        if (!isConnected) {
            Log.w(TAG, "Not connected, dropping audio chunk")
            return
        }
        webSocket?.send(okio.ByteString.of(audioChunk, 0, audioChunk.size))
    }

    fun disconnect() {
        isConnected = false
        webSocket?.close(1000, "Client disconnect")
        webSocket = null
        clientScope.cancel()
    }

    // --- Keystore Auth Token Management ---

    private fun getAuthToken(): String? {
        return try {
            val context = MeetingAssistantApp.instance?.applicationContext ?: return null
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

            val encryptedToken = prefs.getString(ENCRYPTED_TOKEN_KEY, null)
            val ivString = prefs.getString(IV_PREF_KEY, null)

            if (encryptedToken == null || ivString == null) {
                Log.w(TAG, "No auth token stored in Keystore")
                return null
            }

            val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
            keyStore.load(null)
            val key = keyStore.getKey(KEY_ALIAS, null) as SecretKey

            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            val iv = Base64.decode(ivString, Base64.DEFAULT)
            cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, iv))

            val encrypted = Base64.decode(encryptedToken, Base64.DEFAULT)
            val decrypted = cipher.doFinal(encrypted)

            String(decrypted, Charsets.UTF_8)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to decrypt auth token: ${e.message}")
            null
        }
    }

    fun storeAuthToken(token: String) {
        try {
            val context = MeetingAssistantApp.instance?.applicationContext ?: return
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

            val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
            keyStore.load(null)

            if (!keyStore.containsAlias(KEY_ALIAS)) {
                generateKey()
            }

            val key = keyStore.getKey(KEY_ALIAS, null) as SecretKey

            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.ENCRYPT_MODE, key)

            val iv = cipher.iv
            val encrypted = cipher.doFinal(token.toByteArray(Charsets.UTF_8))

            prefs.edit()
                .putString(ENCRYPTED_TOKEN_KEY, Base64.encodeToString(encrypted, Base64.DEFAULT))
                .putString(IV_PREF_KEY, Base64.encodeToString(iv, Base64.DEFAULT))
                .apply()

            Log.d(TAG, "Auth token stored securely in Keystore")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to store auth token: ${e.message}")
        }
    }

    private fun generateKey() {
        val keyGenerator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        keyGenerator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build()
        )
        keyGenerator.generateKey()
    }

}
