package com.edu.hackyeah.components

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.SmallFloatingActionButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edu.hackyeah.network.IncidentService
import com.edu.hackyeah.network.IncidentItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import com.edu.hackyeah.location.LocationHelper
import androidx.compose.runtime.rememberCoroutineScope
import kotlinx.coroutines.launch

data class Incident(
    val type: String,
    val location: String,
    val description: String,
    val time: String,
    val icon: ImageVector,
    val color: Color,
    val latitude: Double? = null,
    val longitude: Double? = null
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IncidentsScreen(outerPadding: androidx.compose.foundation.layout.PaddingValues = androidx.compose.foundation.layout.PaddingValues(0.dp)) {
    var showReportDialog by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var incidents by remember { mutableStateOf(listOf<Incident>()) }
    var selectedIncident by remember { mutableStateOf<Incident?>(null) }
    var mapView by remember { mutableStateOf<org.osmdroid.views.MapView?>(null) }
    val context = LocalContext.current
    val locationHelper = remember { LocationHelper(context) }
    val coroutineScope = rememberCoroutineScope()

    // Ask for location and load incidents within 1km of current location
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions: Map<String, @JvmSuppressWildcards Boolean> ->
        val granted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
                permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (granted) {
            coroutineScope.launch {
                isLoading = true
                errorMessage = null
                val current = locationHelper.getCurrentLocation()
                if (current != null) {
                    val result = withContext(Dispatchers.IO) {
                        IncidentService.fetchIncidentsByCoordinates(
                            coordinates = listOf(current.latitude to current.longitude),
                            maxDistanceKm = 1.0
                        )
                    }
                    result.onSuccess { list ->
                        incidents = list.mapNotNull { it.toUiIncident() }
                        isLoading = false
                    }.onFailure { e ->
                        errorMessage = e.message ?: "Nie udało się pobrać incydentów"
                        isLoading = false
                    }
                } else {
                    errorMessage = "Nie udało się pobrać lokalizacji urządzenia"
                    isLoading = false
                }
            }
        } else {
            errorMessage = "Brak uprawnień do lokalizacji"
        }
    }

    // Trigger permission request on enter
    LaunchedEffect(Unit) {
        permissionLauncher.launch(
            arrayOf(
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            )
        )
    }

    if (showReportDialog) {
        ReportIncidentDialog(
            onDismiss = { showReportDialog = false },
            onSuccess = {
                // Odśwież listę incydentów
            }
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(outerPadding)
            .background(Color(0xFFF5F5F5))
            .padding(16.dp)
    ) {
        // Map with incident markers + quick recenter button
        val incidentMarkers = incidents.filter { it.latitude != null && it.longitude != null }
            .map { 
                com.edu.hackyeah.location.LocationPoint(
                    latitude = it.latitude!!,
                    longitude = it.longitude!!,
                    address = "${it.type}: ${it.description}"
                )
            }
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(300.dp)
        ) {
            Map(
                modifier = Modifier
                    .fillMaxSize(),
                userMarkers = incidentMarkers,
                enableMyLocation = true,
                routePoints = emptyList(),
                onMapReady = { map ->
                    mapView = map
                }
            )

            SmallFloatingActionButton(
                onClick = {
                    coroutineScope.launch {
                        val current = locationHelper.getCurrentLocation()
                        if (current != null && mapView != null) {
                            val gp = org.osmdroid.util.GeoPoint(current.latitude, current.longitude)
                            android.os.Handler(android.os.Looper.getMainLooper()).post {
                                mapView?.controller?.animateTo(gp)
                                mapView?.controller?.setZoom(15.0)
                            }
                        } else if (mapView == null) {
                            errorMessage = "Mapa jeszcze się nie załadowała"
                        } else {
                            errorMessage = "Nie udało się pobrać lokalizacji"
                        }
                    }
                },
                containerColor = Color(0xFF1976D2),
                contentColor = Color.White,
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(12.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.MyLocation,
                    contentDescription = "Pokaż moją lokalizację"
                )
            }
        }
        Spacer(modifier = Modifier.height(16.dp))

        // Simple Add Button
        Button(
            onClick = { showReportDialog = true },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0xFF1976D2)
            ),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(
                Icons.Default.Add,
                contentDescription = "Dodaj",
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                "Zgłoś incydent",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // State rendering
        when {
            isLoading -> {
                Text(text = "Ładowanie incydentów...", color = Color(0xFF757575))
            }
            errorMessage != null -> {
                Text(text = errorMessage!!, color = Color(0xFFD32F2F))
            }
            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(incidents.size) { index ->
                        IncidentCard(
                            incident = incidents[index],
                            onClick = { selectedIncident = incidents[index] }
                        )
                    }
                }
            }
        }
    }

    // Zoom to selected incident on map when clicked
    LaunchedEffect(selectedIncident) {
        selectedIncident?.let { incident ->
            if (incident.latitude != null && incident.longitude != null && mapView != null) {
                val geoPoint = org.osmdroid.util.GeoPoint(incident.latitude, incident.longitude)
                android.os.Handler(android.os.Looper.getMainLooper()).post {
                    mapView?.controller?.animateTo(geoPoint)
                    mapView?.controller?.setZoom(16.0)
                }
            }
        }
    }
}

// Map API model to UI model
private fun IncidentItem.toUiIncident(): Incident? {
    val cat = (category ?: "").lowercase()
    val (icon, color, typeLabel) = when (cat) {
        "wypadek_drogowy", "accident", "crash" -> Triple(Icons.Default.Warning, Color(0xFFD32F2F), "Wypadek drogowy")
        "korek", "traffic", "jam" -> Triple(Icons.Default.Info, Color(0xFFF57C00), "Korek")
        else -> Triple(Icons.Default.Info, Color(0xFF1976D2), category ?: "Zgłoszenie")
    }
    val locText = if (latitude != null && longitude != null) {
        "${"%.5f".format(latitude)}, ${"%.5f".format(longitude)}"
    } else {
        "Brak lokalizacji"
    }
    return Incident(
        type = typeLabel,
        location = locText,
        description = description ?: "",
        time = createdAt ?: "",
        icon = icon,
        color = color,
        latitude = latitude,
        longitude = longitude
    )
}

@Composable
fun IncidentCard(incident: Incident, onClick: (() -> Unit)? = null) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = onClick != null) { onClick?.invoke() },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.Top
        ) {
            // Icon
            Icon(
                incident.icon,
                contentDescription = null,
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(incident.color.copy(alpha = 0.1f))
                    .padding(12.dp),
                tint = incident.color
            )

            // Content
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 12.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = incident.type,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF212121)
                    )
                    Text(
                        text = incident.time,
                        fontSize = 12.sp,
                        color = Color(0xFF757575)
                    )
                }

                Text(
                    text = incident.location,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF1976D2),
                    modifier = Modifier.padding(top = 4.dp)
                )

                Text(
                    text = incident.description,
                    fontSize = 14.sp,
                    color = Color(0xFF757575),
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}
