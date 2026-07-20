package com.jarvis.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Logout
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.jarvis.app.ui.JarvisTheme
import kotlinx.coroutines.launch

private data class Msg(val role: String, val text: String)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val store = Store(this)
        setContent { JarvisTheme { App(store) } }
    }
}

@Composable
private fun App(store: Store) {
    var client by remember { mutableStateOf<ApiClient?>(null) }
    var checking by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        val url = store.serverUrl
        val token = store.token
        if (url.isNotEmpty() && token.isNotEmpty()) {
            val candidate = runCatching { ApiClient(url, token) }.getOrNull()
            if (candidate != null && runCatching { candidate.me() }.isSuccess) {
                client = candidate
            } else {
                store.clear()
            }
        }
        checking = false
    }

    Surface(modifier = Modifier.fillMaxSize()) {
        when {
            checking -> Box(Modifier.fillMaxSize(), Alignment.Center) {
                CircularProgressIndicator()
            }
            client == null -> LoginScreen(store) { client = it }
            else -> ChatScreen(client!!, store.username) {
                scope.launch { runCatching { client!!.logout() } }
                store.clear()
                client = null
            }
        }
    }
}

@Composable
private fun LoginScreen(store: Store, onSignedIn: (ApiClient) -> Unit) {
    var server by remember { mutableStateOf(store.serverUrl.ifEmpty { "https://" }) }
    var username by remember { mutableStateOf(store.username) }
    var password by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Column(
        Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("J.A.R.V.I.S.", fontSize = 30.sp, fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.height(24.dp))
        OutlinedTextField(server, { server = it }, label = { Text("Server URL") },
            singleLine = true, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(username, { username = it }, label = { Text("Username") },
            singleLine = true, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(password, { password = it }, label = { Text("Password") },
            singleLine = true, visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = {
                busy = true
                status = ""
                scope.launch {
                    try {
                        val c = ApiClient(server.trim())
                        c.login(username.trim(), password)
                        store.serverUrl = c.baseUrl
                        store.username = username.trim()
                        store.token = c.token
                        onSignedIn(c)
                    } catch (e: Exception) {
                        status = e.message ?: "Sign-in failed"
                    } finally {
                        busy = false
                    }
                }
            },
            enabled = !busy,
            modifier = Modifier.fillMaxWidth().height(50.dp),
        ) { Text(if (busy) "Signing in…" else "Sign in") }
        if (status.isNotEmpty()) {
            Spacer(Modifier.height(12.dp))
            Text(status, color = MaterialTheme.colorScheme.error)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChatScreen(client: ApiClient, username: String, onLogout: () -> Unit) {
    val messages = remember { mutableStateListOf<Msg>() }
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    fun send() {
        val text = input.trim()
        if (text.isEmpty() || busy) return
        input = ""
        messages.add(Msg("user", text))
        val idx = messages.size
        messages.add(Msg("assistant", ""))
        busy = true
        scope.launch {
            try {
                client.chatStream(text) { piece ->
                    messages[idx] = messages[idx].copy(text = messages[idx].text + piece)
                }
            } catch (e: Exception) {
                messages[idx] = Msg("assistant", "⚠️ ${e.message}")
            } finally {
                busy = false
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("J.A.R.V.I.S.", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = onLogout) {
                        Icon(Icons.Filled.Logout, contentDescription = "Logout")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                ),
            )
        },
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad)) {
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).fillMaxWidth().padding(horizontal = 12.dp),
            ) {
                items(messages) { msg -> Bubble(msg) }
            }
            Row(
                Modifier.fillMaxWidth().padding(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    input, { input = it },
                    placeholder = { Text("Message…") },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions.Default,
                )
                Spacer(Modifier.width(8.dp))
                IconButton(onClick = { send() }, enabled = !busy) {
                    Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send",
                        tint = MaterialTheme.colorScheme.primary)
                }
            }
        }
    }
}

@Composable
private fun Bubble(msg: Msg) {
    val isUser = msg.role == "user"
    val bg = if (isUser) MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)
    else MaterialTheme.colorScheme.surfaceVariant
    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = bg),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text(
                text = if (isUser) msg.text else "J.A.R.V.I.S.: ${msg.text}",
                modifier = Modifier.padding(12.dp),
                color = MaterialTheme.colorScheme.onSurface,
            )
        }
    }
}
