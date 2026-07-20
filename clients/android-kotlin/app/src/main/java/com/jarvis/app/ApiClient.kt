package com.jarvis.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Thrown when the server rejects a request. */
class ApiException(val status: Int, message: String) : Exception(message)

/**
 * Minimal client for the J.A.R.V.I.S. HTTP API — standard library only
 * (HttpURLConnection + org.json), no third-party HTTP dependency.
 */
class ApiClient(baseUrl: String, var token: String = "") {

    val baseUrl: String = baseUrl.trimEnd('/')

    init {
        require(this.baseUrl.startsWith("http://") ||
            this.baseUrl.startsWith("https://")) {
            "Server URL must start with http:// or https://"
        }
    }

    private fun open(method: String, path: String): HttpURLConnection {
        val conn = URL("$baseUrl$path").openConnection() as HttpURLConnection
        conn.requestMethod = method
        conn.connectTimeout = 15000
        conn.readTimeout = 120000
        conn.setRequestProperty("Content-Type", "application/json")
        if (token.isNotEmpty()) {
            conn.setRequestProperty("Authorization", "Bearer $token")
        }
        return conn
    }

    private fun errorDetail(conn: HttpURLConnection): String = try {
        val body = conn.errorStream?.bufferedReader()?.readText().orEmpty()
        JSONObject(body).optString("detail", "HTTP ${conn.responseCode}")
    } catch (_: Exception) {
        "HTTP ${conn.responseCode}"
    }

    private suspend fun request(method: String, path: String, body: JSONObject?): JSONObject =
        withContext(Dispatchers.IO) {
            val conn = open(method, path)
            try {
                if (body != null) {
                    conn.doOutput = true
                    conn.outputStream.use { it.write(body.toString().toByteArray()) }
                }
                val code = conn.responseCode
                if (code !in 200..299) throw ApiException(code, errorDetail(conn))
                val text = conn.inputStream.bufferedReader().readText()
                if (text.isBlank()) JSONObject() else JSONObject(text)
            } finally {
                conn.disconnect()
            }
        }

    suspend fun login(username: String, password: String): String {
        val out = request("POST", "/auth/login",
            JSONObject().put("username", username).put("password", password))
        token = out.getString("token")
        return token
    }

    suspend fun me(): String = request("GET", "/auth/me", null).getString("username")

    suspend fun logout() {
        try { request("POST", "/auth/logout", null) } finally { token = "" }
    }

    /** Available model profiles the user can switch between (may be empty). */
    suspend fun models(): List<String> {
        val arr = request("GET", "/models", null).optJSONArray("models")
            ?: return emptyList()
        return (0 until arr.length()).map { arr.getString(it) }
    }

    /** Get a pairing code to link this account's Telegram (send /link CODE). */
    suspend fun pairingCode(): String =
        request("POST", "/auth/pairing-code", null).getString("code")

    /**
     * Stream a reply from /chat/stream, invoking [onChunk] on the IO thread for
     * each text piece. Returns the full reply.
     */
    suspend fun chatStream(
        message: String,
        sessionId: String = "android",
        model: String? = null,
        language: String? = null,
        onChunk: (String) -> Unit,
    ): String = withContext(Dispatchers.IO) {
        val conn = open("POST", "/chat/stream")
        conn.doOutput = true
        val body = JSONObject().put("message", message).put("session_id", sessionId)
        if (!model.isNullOrEmpty()) body.put("model", model)
        if (!language.isNullOrEmpty()) body.put("language", language)
        conn.outputStream.use { it.write(body.toString().toByteArray()) }
        try {
            val code = conn.responseCode
            if (code !in 200..299) throw ApiException(code, errorDetail(conn))
            val sb = StringBuilder()
            val reader = conn.inputStream.bufferedReader()
            val buf = CharArray(1024)
            while (true) {
                val n = reader.read(buf)
                if (n < 0) break
                val piece = String(buf, 0, n)
                sb.append(piece)
                onChunk(piece)
            }
            sb.toString()
        } finally {
            conn.disconnect()
        }
    }
}
