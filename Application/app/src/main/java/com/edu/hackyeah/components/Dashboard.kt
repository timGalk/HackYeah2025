package com.edu.hackyeah.components

import android.Manifest
import android.annotation.SuppressLint
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.outlined.TripOrigin
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edu.hackyeah.location.DestinationPoint
import com.edu.hackyeah.location.TransportRouteResult
import kotlinx.coroutines.launch
import com.edu.hackyeah.location.LocationHelper
import java.time.Instant


@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Dashboard() {
    var destinationPoints by remember {
        mutableStateOf<List<DestinationPoint>>(
            emptyList()
        )
    }
    var fromLocation by remember { mutableStateOf("") }
    var toLocation by remember { mutableStateOf("") }
    var showRouteTile by remember { mutableStateOf(false) }
    var showRouteDetails by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isSearching by remember { mutableStateOf(false) }
    var routeResult by remember { mutableStateOf<TransportRouteResult?>(null) }
    val context = LocalContext.current
    val locationHelper = remember { LocationHelper(context) }
    val coroutineScope = rememberCoroutineScope()

    // Load available stop names
    val availableStops = remember { locationHelper.getAllStopNames() }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions: Map<String, @JvmSuppressWildcards Boolean> ->
        if (permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true || permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true) {
            coroutineScope.launch {
                try {
                    @SuppressLint("MissingPermission")
                    val address = locationHelper.getCurrentAddress()
                    if (address != null) {
                        fromLocation = address
                        errorMessage = null
                    } else {
                        errorMessage = "Nie można pobrać lokalizacji. Upewnij się, że GPS jest włączony."
                    }
                } catch (e: Exception) {
                    errorMessage = "Błąd podczas pobierania lokalizacji: ${e.message}"
                }
            }
        } else {
            errorMessage = "Brak uprawnień do lokalizacji"
        }
    }

    // Show route details view when clicked
    if (showRouteDetails) {
        RouteDetailsView(
            routeResult = routeResult ?: return,
            onBackClick = {
                showRouteDetails = false
            }
        )
        return
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = Color(0xFFF8F9FA)
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            Color(0xFFE3F2FD),
                            Color(0xFFF8F9FA)
                        )
                    )
                )
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(20.dp)
            ) {
                // Welcome Card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = Color.White
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp)
                    ) {
                        Text(
                            "Journey Radar",
                            fontSize = 24.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1976D2)
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            "Znajdź najlepszą trasę do swojego celu",
                            fontSize = 14.sp,
                            color = Color(0xFF666666)
                        )
                    }
                }

                // Search Card
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .shadow(
                            elevation = 8.dp,
                            shape = RoundedCornerShape(20.dp),
                            spotColor = Color(0xFF1976D2).copy(alpha = 0.1f)
                        ),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    shape = RoundedCornerShape(20.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(24.dp),
                        verticalArrangement = Arrangement.spacedBy(20.dp)
                    ) {
                        Text(
                            "Planuj trasę",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF333333)
                        )

                        // From Location with icon indicator
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(10.dp)
                                        .background(Color(0xFF4CAF50), CircleShape)
                                )
                                Text(
                                    "Punkt startowy",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = Color(0xFF666666)
                                )
                            }

                            AutocompleteStopField(
                                value = fromLocation,
                                onValueChange = { fromLocation = it },
                                placeholder = "Wpisz nazwę przystanku",
                                availableStops = availableStops,
                                leadingIcon = {
                                    Icon(
                                        Icons.Outlined.TripOrigin,
                                        contentDescription = null,
                                        tint = Color(0xFF4CAF50),
                                        modifier = Modifier.size(22.dp)
                                    )
                                },
                                trailingIcon = {
                                    IconButton(
                                        onClick = {
                                            permissionLauncher.launch(
                                                arrayOf(
                                                    Manifest.permission.ACCESS_FINE_LOCATION,
                                                    Manifest.permission.ACCESS_COARSE_LOCATION
                                                )
                                            )
                                        },
                                        colors = IconButtonDefaults.iconButtonColors(
                                            containerColor = Color(0xFF1976D2).copy(alpha = 0.1f)
                                        ),
                                        modifier = Modifier.size(40.dp)
                                    ) {
                                        Icon(
                                            Icons.Default.MyLocation,
                                            contentDescription = "Użyj mojej lokalizacji",
                                            tint = Color(0xFF1976D2),
                                            modifier = Modifier.size(20.dp)
                                        )
                                    }
                                }
                            )
                        }

                        // Swap Button
                        Box(
                            modifier = Modifier.fillMaxWidth(),
                            contentAlignment = Alignment.Center
                        ) {
                            IconButton(
                                onClick = {
                                    // Swap locations
                                    val temp = fromLocation
                                    fromLocation = toLocation
                                    toLocation = temp
                                },
                                colors = IconButtonDefaults.iconButtonColors(
                                    containerColor = Color(0xFF1976D2).copy(alpha = 0.1f)
                                ),
                                modifier = Modifier.size(48.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                                    contentDescription = "Zamień miejscami",
                                    tint = Color(0xFF1976D2),
                                    modifier = Modifier.size(24.dp)
                                )
                            }
                        }

                        // To Location with icon indicator
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(10.dp)
                                        .background(Color(0xFFF44336), CircleShape)
                                )
                                Text(
                                    "Punkt docelowy",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = Color(0xFF666666)
                                )
                            }

                            AutocompleteStopField(
                                value = toLocation,
                                onValueChange = { toLocation = it },
                                placeholder = "Dokąd chcesz pojechać?",
                                availableStops = availableStops,
                                leadingIcon = {
                                    Icon(
                                        Icons.Default.Place,
                                        contentDescription = null,
                                        tint = Color(0xFFF44336),
                                        modifier = Modifier.size(22.dp)
                                    )
                                }
                            )
                        }

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

                                        println("Searching transport route from: $fromLocation to: $toLocation")

                                        // Get transport route from new API
                                        val result = locationHelper.getTransportRoute(
                                            sourceAddress = fromLocation,
                                            targetAddress = toLocation
                                        )

                                        if (result == null) {
                                            errorMessage = "Nie znaleziono trasy. Sprawdź nazwy przystanków."
                                            isSearching = false
                                            return@launch
                                        }

                                        // Update route result and destination points
                                        routeResult = result
                                        destinationPoints = result.defaultPath

                                        // Show incident warning if detected
                                        if (result.incidentDetected) {
                                            errorMessage = result.message ?: "Wykryto incydent na trasie - pokazano alternatywną trasę"
                                        }

                                        // Show route tile with real data
                                        showRouteTile = true
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
                                .height(56.dp)
                                .shadow(
                                    elevation = 4.dp,
                                    shape = RoundedCornerShape(12.dp),
                                    spotColor = Color(0xFF1976D2).copy(alpha = 0.3f)
                                ),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFF1976D2),
                                disabledContainerColor = Color(0xFFBDBDBD)
                            ),
                            shape = RoundedCornerShape(12.dp),
                            enabled = fromLocation.isNotBlank() && toLocation.isNotBlank() && !isSearching
                        ) {
                            Icon(
                                Icons.Default.Search,
                                contentDescription = null,
                                modifier = Modifier.size(22.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                if (isSearching) "Wyszukiwanie..." else "Znajdź trasę",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.SemiBold,
                                letterSpacing = 0.5.sp
                            )
                        }

                        // Error message
                        if (errorMessage != null) {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(
                                    containerColor = Color(0xFFFFEBEE)
                                ),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Text(
                                    text = errorMessage!!,
                                    color = Color(0xFFD32F2F),
                                    fontSize = 13.sp,
                                    modifier = Modifier.padding(12.dp),
                                    lineHeight = 18.sp
                                )
                            }
                        }
                    }
                }

                // Route Tile - displayed with real data
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
}
