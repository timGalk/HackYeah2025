package com.edu.hackyeah.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector

sealed class NavigationItem(
    val route: String,
    val icon: ImageVector,
    val label: String
) {
    object Home : NavigationItem("home", Icons.Default.Home, "Trasy")
    object Incidents : NavigationItem("incidents", Icons.Default.Warning, "Incydenty")
    object Profile : NavigationItem("profile", Icons.Default.Person, "Profil")
    object Settings : NavigationItem("settings", Icons.Default.Settings, "Ustawienia")
}

@Composable
fun MainNavigation() {
    var selectedItemIndex by remember { mutableIntStateOf(0) }

    val navigationItems = listOf(
        NavigationItem.Home,
        NavigationItem.Incidents,
        NavigationItem.Profile,
        NavigationItem.Settings
    )

    Scaffold(
        bottomBar = {
            NavigationBar(
                containerColor = Color.White,
                contentColor = Color(0xFF1976D2)
            ) {
                navigationItems.forEachIndexed { index, item ->
                    NavigationBarItem(
                        selected = selectedItemIndex == index,
                        onClick = { selectedItemIndex = index },
                        icon = {
                            Icon(
                                imageVector = item.icon,
                                contentDescription = item.label
                            )
                        },
                        label = { Text(item.label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = Color(0xFF1976D2),
                            selectedTextColor = Color(0xFF1976D2),
                            unselectedIconColor = Color(0xFF757575),
                            unselectedTextColor = Color(0xFF757575),
                            indicatorColor = Color(0xFF1976D2).copy(alpha = 0.1f)
                        )
                    )
                }
            }
        }
    ) { paddingValues ->
        when (selectedItemIndex) {
            0 -> Dashboard()
            1 -> IncidentsScreen(paddingValues)
            2 -> ProfileScreen()
            3 -> SettingsScreen()
        }
    }
}
