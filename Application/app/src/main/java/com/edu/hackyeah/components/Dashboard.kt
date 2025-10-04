package com.edu.hackyeah.components

import android.Manifest
import android.annotation.SuppressLint
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edu.hackyeah.location.DestinationPoint
import kotlinx.coroutines.launch
import com.edu.hackyeah.location.LocationHelper
import java.time.Instant


@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Dashboard() {
    var destinationPoints by remember {
        mutableStateOf<List<DestinationPoint>>(
            listOf(
                DestinationPoint("Kraków Główny", Instant.parse("2024-01-15T08:00:00Z")),
                DestinationPoint("Rynek Główny", Instant.parse("2024-01-15T08:15:00Z")),
                DestinationPoint("Wawel", Instant.parse("2024-01-15T08:30:00Z")),
                DestinationPoint("Kazimierz", Instant.parse("2024-01-15T08:45:00Z")),
                DestinationPoint("Nowa Huta", Instant.parse("2024-01-15T09:00:00Z")),
                DestinationPoint("Podgórze", Instant.parse("2024-01-15T09:15:00Z")),
                DestinationPoint("Bronowice", Instant.parse("2024-01-15T09:30:00Z")),
                DestinationPoint("Krowodrza", Instant.parse("2024-01-15T09:45:00Z"))
            )
        )
    }
    var fromLocation by remember { mutableStateOf("") }
    var toLocation by remember { mutableStateOf("") }
    var showRouteTile by remember { mutableStateOf(false) }
    var showRouteDetails by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isSearching by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val locationHelper = remember { LocationHelper(context) }
    val coroutineScope = rememberCoroutineScope()

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions: Map<String, @JvmSuppressWildcards Boolean> ->
        if (permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true || permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true) {
            coroutineScope.launch {
                @SuppressLint("MissingPermission")
                val address = locationHelper.getCurrentAddress()
                address?.let {
                    fromLocation = it
                }
            }
        }
    }

    // Show route details view when clicked
    if (showRouteDetails) {
        RouteDetailsView(
            destinationPoints = destinationPoints,
            onBackClick = {
                showRouteDetails = false
            }
        )
        return
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        "KAWKA GUROM",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1976D2),
                    titleContentColor = Color.White
                )
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(Color(0xFFF5F5F5))
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Search Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // From Location
                    OutlinedTextField(
                        value = fromLocation,
                        onValueChange = { fromLocation = it },
                        placeholder = { Text("Skąd?") },
                        modifier = Modifier.fillMaxWidth(),
                        leadingIcon = {
                            Icon(
                                Icons.Default.Place,
                                contentDescription = null,
                                tint = Color(0xFF4CAF50)
                            )
                        },
                        trailingIcon = {
                            IconButton(onClick = {
                                permissionLauncher.launch(
                                    arrayOf(
                                        Manifest.permission.ACCESS_FINE_LOCATION,
                                        Manifest.permission.ACCESS_COARSE_LOCATION
                                    )
                                )
                            }) {
                                Icon(
                                    Icons.Default.Place,
                                    contentDescription = "Pobierz aktualną lokalizację",
                                    tint = Color(0xFF1976D2)
                                )
                            }
                        },
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Color(0xFF1976D2),
                            unfocusedBorderColor = Color(0xFFE0E0E0)
                        ),
                        shape = RoundedCornerShape(8.dp)
                    )

                    // To Location
                    OutlinedTextField(
                        value = toLocation,
                        onValueChange = { toLocation = it },
                        placeholder = { Text("Dokąd?") },
                        modifier = Modifier.fillMaxWidth(),
                        leadingIcon = {
                            Icon(
                                Icons.Default.Place,
                                contentDescription = null,
                                tint = Color(0xFFF44336)
                            )
                        },
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Color(0xFF1976D2),
                            unfocusedBorderColor = Color(0xFFE0E0E0)
                        ),
                        shape = RoundedCornerShape(8.dp)
                    )

                    // Search Button
                    Button(
                        onClick = {
                            errorMessage = null
                            isSearching = true

                            coroutineScope.launch {
                                try {
                                    // Validate inputs
                                    if (fromLocation.length < 3 || toLocation.length < 3) {
                                        errorMessage = "Proszę wpisać pełne adresy (minimum 3 znaki)"
                                        isSearching = false
                                        return@launch
                                    }

                                    println("Searching from: $fromLocation to: $toLocation")

                                    // Geocode from location
                                    val startPoint = locationHelper.getCoordinatesFromAddress(fromLocation)
                                    if (startPoint == null) {
                                        errorMessage = "Nie znaleziono adresu początkowego: $fromLocation"
                                        isSearching = false
                                        return@launch
                                    }

                                    // Geocode to location
                                    val endPoint = locationHelper.getCoordinatesFromAddress(toLocation)
                                    if (endPoint == null) {
                                        errorMessage = "Nie znaleziono adresu docelowego: $toLocation"
                                        isSearching = false
                                        return@launch
                                    }

                                    println("Geocoded: Start=$startPoint, End=$endPoint")

                                    // Show route tile with static data
                                    showRouteTile = true
                                    errorMessage = null
                                    isSearching = false

                                } catch (e: Exception) {
                                    errorMessage = "Błąd wyszukiwania: ${e.message}"
                                    isSearching = false
                                    e.printStackTrace()
                                }
                            }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF1976D2)
                        ),
                        shape = RoundedCornerShape(8.dp),
                        enabled = fromLocation.isNotBlank() && toLocation.isNotBlank() && !isSearching
                    ) {
                        Icon(
                            Icons.Default.Search,
                            contentDescription = null,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            if (isSearching) "Wyszukiwanie..." else "Wyszukaj",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    // Error message
                    if (errorMessage != null) {
                        Text(
                            text = errorMessage!!,
                            color = Color(0xFFD32F2F),
                            fontSize = 14.sp,
                            modifier = Modifier.padding(top = 8.dp)
                        )
                    }
                }
            }

            // Route Tile - displayed with static data
            if (showRouteTile) {
                RouteTile(
                    destinationPoints = destinationPoints,
                    onClick = {
                        showRouteDetails = true
                    }
                )
            }
        }
    }
}