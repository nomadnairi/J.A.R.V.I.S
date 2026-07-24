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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.toMutableStateList
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.jarvis.app.ui.JarvisTheme
import kotlinx.coroutines.launch
import java.util.UUID

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val store = Store(this)
        setContent {
            var themeMode by remember { mutableStateOf(store.themeMode) }
            JarvisTheme(themeMode) {
                App(store, onThemeChange = { themeMode = it; store.themeMode = it })
            }
        }
    }
}

@Composable
private fun App(store: Store, onThemeChange: (String) -> Unit) {
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
                store.clearSession()
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
            else -> HomeScreen(client!!, store, onThemeChange) {
                scope.launch { runCatching { client!!.logout() } }
                store.clearSession()
                client = null
            }
        }
    }
}

// -- login --------------------------------------------------------------------

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
                busy = true; status = ""
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

// -- home (drawer + chat + settings) -----------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun HomeScreen(
    client: ApiClient,
    store: Store,
    onThemeChange: (String) -> Unit,
    onLogout: () -> Unit,
) {
    val conversations = remember {
        store.loadConversations().ifEmpty {
            mutableListOf(Conversation("android-" + UUID.randomUUID(), "New chat"))
        }.toMutableStateList()
    }
    var current by remember { mutableStateOf(conversations.first()) }
    var showSettings by remember { mutableStateOf(false) }
    var models by remember { mutableStateOf(listOf<String>()) }
    var model by remember { mutableStateOf(store.model) }
    var language by remember { mutableStateOf(store.language) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) { models = runCatching { client.models() }.getOrDefault(emptyList()) }

    fun persist() = store.saveConversations(conversations)

    val drawerState = androidx.compose.material3.rememberDrawerState(
        androidx.compose.material3.DrawerValue.Closed)

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                Text("J.A.R.V.I.S.", fontWeight = FontWeight.Bold, fontSize = 22.sp,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(16.dp))
                NavigationDrawerItem(
                    label = { Text("New chat") },
                    selected = false,
                    icon = { Icon(Icons.Filled.Add, null) },
                    onClick = {
                        val c = Conversation("android-" + UUID.randomUUID(), "New chat")
                        conversations.add(0, c); current = c; persist()
                        scope.launch { drawerState.close() }
                    },
                )
                Divider()
                conversations.forEach { conv ->
                    NavigationDrawerItem(
                        label = { Text(conv.title, maxLines = 1) },
                        selected = conv.id == current.id,
                        onClick = {
                            current = conv
                            scope.launch { drawerState.close() }
                        },
                    )
                }
                Divider()
                NavigationDrawerItem(
                    label = { Text("Settings") },
                    selected = false,
                    icon = { Icon(Icons.Filled.Settings, null) },
                    onClick = { showSettings = true; scope.launch { drawerState.close() } },
                )
            }
        },
    ) {
        if (showSettings) {
            SettingsScreen(
                store = store, client = client, models = models,
                model = model, onModel = { model = it; store.model = it },
                language = language, onLanguage = { language = it; store.language = it },
                onThemeChange = onThemeChange,
                onBack = { showSettings = false },
                onLogout = onLogout,
            )
        } else {
            ChatScreen(
                client = client, conversation = current, model = model,
                language = language,
                onOpenDrawer = { scope.launch { drawerState.open() } },
                onChanged = {
                    // First user message becomes the conversation title.
                    if (current.title == "New chat") {
                        val firstUser = current.messages.firstOrNull { it.role == "user" }
                        if (firstUser != null) current.title = firstUser.text.take(30)
                    }
                    persist()
                },
            )
        }
    }
}

// -- chat ---------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChatScreen(
    client: ApiClient,
    conversation: Conversation,
    model: String,
    language: String,
    onOpenDrawer: () -> Unit,
    onChanged: () -> Unit,
) {
    val messages = remember(conversation.id) { conversation.messages.toMutableStateList() }
    var input by remember(conversation.id) { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()
    val clipboard = LocalClipboardManager.current

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    fun sync() { conversation.messages.clear(); conversation.messages.addAll(messages); onChanged() }

    fun send() {
        val text = input.trim()
        if (text.isEmpty() || busy) return
        input = ""
        messages.add(Msg("user", text))
        val idx = messages.size
        messages.add(Msg("assistant", ""))
        busy = true
        sync()
        scope.launch {
            try {
                client.chatStream(text, conversation.id, model, language) { piece ->
                    messages[idx] = messages[idx].copy(text = messages[idx].text + piece)
                }
            } catch (e: Exception) {
                messages[idx] = Msg("assistant", "⚠️ ${e.message}")
            } finally {
                busy = false
                sync()
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(conversation.title, maxLines = 1,
                    fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onOpenDrawer) {
                        Icon(Icons.Filled.Menu, contentDescription = "Menu")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface),
            )
        },
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad)) {
            if (messages.isEmpty()) {
                Box(Modifier.weight(1f).fillMaxWidth(), Alignment.Center) {
                    Text("Ask me anything, Sir.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).fillMaxWidth()
                        .padding(horizontal = 12.dp),
                ) {
                    items(messages) { msg ->
                        Bubble(msg) { clipboard.setText(AnnotatedString(msg.text)) }
                    }
                }
            }
            Row(
                Modifier.fillMaxWidth().padding(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    input, { input = it },
                    placeholder = { Text("Message…") },
                    modifier = Modifier.weight(1f),
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Bubble(msg: Msg, onLongPress: () -> Unit) {
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
            onClick = onLongPress,
        ) {
            Text(
                text = if (isUser) msg.text else "J.A.R.V.I.S.: ${msg.text}",
                modifier = Modifier.padding(12.dp),
                color = MaterialTheme.colorScheme.onSurface,
            )
        }
    }
}

// -- settings -----------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SettingsScreen(
    store: Store,
    client: ApiClient,
    models: List<String>,
    model: String,
    onModel: (String) -> Unit,
    language: String,
    onLanguage: (String) -> Unit,
    onThemeChange: (String) -> Unit,
    onBack: () -> Unit,
    onLogout: () -> Unit,
) {
    var pairing by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.Menu, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface),
            )
        },
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad).padding(16.dp)) {
            Text("Account: ${store.username}",
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(16.dp))

            Picker("AI model", model.ifEmpty { "Auto" },
                listOf("" to "Auto") + models.map { it to it }) { onModel(it) }
            Spacer(Modifier.height(12.dp))
            Picker("Reply language", language.ifEmpty { "Auto" },
                listOf("" to "Auto", "en" to "English", "ru" to "Русский",
                    "uz" to "O'zbek")) { onLanguage(it) }
            Spacer(Modifier.height(12.dp))
            Picker("Theme", store.themeMode,
                listOf("system" to "System", "dark" to "Dark", "light" to "Light")) {
                onThemeChange(it)
            }

            Spacer(Modifier.height(24.dp))
            Button(onClick = {
                scope.launch {
                    pairing = runCatching { "Send to the bot: /link " + client.pairingCode() }
                        .getOrElse { "Failed: ${it.message}" }
                }
            }, modifier = Modifier.fillMaxWidth()) { Text("Link Telegram") }
            if (pairing.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Text(pairing, color = MaterialTheme.colorScheme.primary)
            }

            Spacer(Modifier.weight(1f))
            TextButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) {
                Text("Sign out", color = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Picker(
    label: String,
    currentLabel: String,
    options: List<Pair<String, String>>,
    onSelect: (String) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    Column {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 13.sp)
        Box {
            Button(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
                Text(options.firstOrNull { it.second == currentLabel || it.first == currentLabel }
                    ?.second ?: currentLabel)
            }
            DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                options.forEach { (value, text) ->
                    DropdownMenuItem(text = { Text(text) }, onClick = {
                        onSelect(value); expanded = false
                    })
                }
            }
        }
    }
}
