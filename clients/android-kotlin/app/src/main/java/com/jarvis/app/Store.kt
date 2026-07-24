package com.jarvis.app

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** A chat message kept locally. */
data class Msg(val role: String, val text: String)

/** A local conversation: its own server session id, title and message cache. */
data class Conversation(
    val id: String,
    var title: String,
    val messages: MutableList<Msg> = mutableListOf(),
)

/**
 * Persistent store for the server URL, login token, username, preferences
 * (theme / model / language) and the local conversation history — all in
 * SharedPreferences as JSON, no database dependency.
 */
class Store(context: Context) {
    private val prefs = context.getSharedPreferences("jarvis", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString("server_url", "") ?: ""
        set(v) = prefs.edit().putString("server_url", v).apply()

    var token: String
        get() = prefs.getString("token", "") ?: ""
        set(v) = prefs.edit().putString("token", v).apply()

    var username: String
        get() = prefs.getString("username", "") ?: ""
        set(v) = prefs.edit().putString("username", v).apply()

    /** Theme mode: "system" | "dark" | "light". */
    var themeMode: String
        get() = prefs.getString("theme_mode", "system") ?: "system"
        set(v) = prefs.edit().putString("theme_mode", v).apply()

    /** Selected model profile ("" = server default). */
    var model: String
        get() = prefs.getString("model", "") ?: ""
        set(v) = prefs.edit().putString("model", v).apply()

    /** Reply language ("" = auto). */
    var language: String
        get() = prefs.getString("language", "") ?: ""
        set(v) = prefs.edit().putString("language", v).apply()

    fun clearSession() = prefs.edit().remove("token").apply()

    // -- conversations --------------------------------------------------------

    fun loadConversations(): MutableList<Conversation> {
        val raw = prefs.getString("conversations", "") ?: ""
        if (raw.isBlank()) return mutableListOf()
        return try {
            val arr = JSONArray(raw)
            (0 until arr.length()).map { i ->
                val obj = arr.getJSONObject(i)
                val msgs = obj.getJSONArray("messages")
                Conversation(
                    id = obj.getString("id"),
                    title = obj.getString("title"),
                    messages = (0 until msgs.length()).map { j ->
                        val m = msgs.getJSONObject(j)
                        Msg(m.getString("role"), m.getString("text"))
                    }.toMutableList(),
                )
            }.toMutableList()
        } catch (_: Exception) {
            mutableListOf()
        }
    }

    fun saveConversations(list: List<Conversation>) {
        val arr = JSONArray()
        for (c in list) {
            val msgs = JSONArray()
            // Cap stored messages per conversation to keep prefs small.
            for (m in c.messages.takeLast(200)) {
                msgs.put(JSONObject().put("role", m.role).put("text", m.text))
            }
            arr.put(JSONObject().put("id", c.id).put("title", c.title)
                .put("messages", msgs))
        }
        prefs.edit().putString("conversations", arr.toString()).apply()
    }
}
