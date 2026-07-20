package com.jarvis.app

import android.content.Context

/** Small persistent store for the server URL, login token and username. */
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

    fun clear() = prefs.edit().remove("token").apply()
}
