package com.jarvis.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Arc-reactor palette to match the desktop app.
private val Accent = Color(0xFF22D3EE)
private val AccentDark = Color(0xFF0E7490)

private val DarkColors = darkColorScheme(
    primary = Accent,
    onPrimary = Color(0xFF0B0F14),
    secondary = AccentDark,
    background = Color(0xFF0B0F14),
    onBackground = Color(0xFFE6EDF3),
    surface = Color(0xFF121821),
    onSurface = Color(0xFFE6EDF3),
    surfaceVariant = Color(0xFF1A2230),
    onSurfaceVariant = Color(0xFF8B98A9),
    outline = Color(0xFF243043),
)

private val LightColors = lightColorScheme(
    primary = Color(0xFF0EA5E9),
    background = Color(0xFFF4F6FB),
    surface = Color(0xFFFFFFFF),
)

@Composable
fun JarvisTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, content = content)
}
