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
import com.edu.hackyeah.location.LocationPoint
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
    var userPoints by remember { mutableStateOf<List<LocationPoint>>(emptyList()) }
    var routePoints by remember { mutableStateOf<List<LocationPoint>>(emptyList()) }
    var showRouteTile by remember { mutableStateOf(false) }
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
                        placeholder = { Text("From where?") },
                        modifier = Modifier.fillMaxWidth(),
                        leadingIcon = {
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
                                    contentDescription = "Get current location",
                                    tint = Color(0xFF4CAF50)
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
                        placeholder = { Text("Where to?") },
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
                            coroutineScope.launch {
                                // Geocode from location
                                val startPoint = locationHelper.getCoordinatesFromAddress(fromLocation)

                                // Geocode to location
                                val endPoint = locationHelper.getCoordinatesFromAddress(toLocation)

                                if (startPoint != null && endPoint != null) {
                                    // Store user-specified points (only A and B)
                                    userPoints = listOf(startPoint, endPoint)

                                    // Get the actual route with all waypoints for drawing the line
                                    val apiRoutePoints = locationHelper.getRoutePoints(
                                        startPoint = startPoint,
                                        endPoint = endPoint,
                                        profile = "driving" // You can change to "walking" or "cycling"
                                    )

                                    if (apiRoutePoints != null && apiRoutePoints.isNotEmpty()) {
                                        // Use the detailed route points for the line
                                        routePoints = apiRoutePoints
                                        println("Found route with ${apiRoutePoints.size} points")
                                    } else {
                                        // Fallback to just start and end points if routing fails
                                        routePoints = listOf(startPoint, endPoint)
                                        println("Using direct route with 2 points")
                                    }
                                } else {
                                    println("Could not geocode addresses")
                                }

                                println("Searching from: $fromLocation to: $toLocation")
                                showRouteTile = true // Show the route tile after search
                            }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF1976D2)
                        ),
                        shape = RoundedCornerShape(8.dp),
                        enabled = fromLocation.isNotBlank() && toLocation.isNotBlank()
                    ) {
                        Icon(
                            Icons.Default.Search,
                            contentDescription = null,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "Search",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }

            // Route Tile - displayed with static data
            if (showRouteTile) {
                RouteTile(
                    destinationPoints = destinationPoints,
                    onClick = {
                        // TODO: Handle route tile click - will show map with route later
                        println("Route tile clicked!")
                    }
                )
            }
        }
    }
}