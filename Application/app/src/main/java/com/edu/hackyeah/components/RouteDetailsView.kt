package com.edu.hackyeah.components

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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edu.hackyeah.location.DestinationPoint
import com.edu.hackyeah.location.LocationHelper
import com.edu.hackyeah.location.LocationPoint
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import java.time.Duration
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RouteDetailsView(
    destinationPoints: List<DestinationPoint>,
    onBackClick: () -> Unit
) {
    val timeFormatter = DateTimeFormatter.ofPattern("HH:mm")
    val context = LocalContext.current
    val locationHelper = remember { LocationHelper(context) }

    var locationPoints by remember { mutableStateOf<List<LocationPoint>>(emptyList()) }
    var routePoints by remember { mutableStateOf<List<LocationPoint>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    // Fetch geolocation for all stops and build route
    LaunchedEffect(destinationPoints) {
        isLoading = true

        // Geocode all destination points in parallel
        coroutineScope {
            val geocodedPoints = destinationPoints.map { point ->
                async {
                    locationHelper.getCoordinatesFromAddress(point.name)
                }
            }.awaitAll().filterNotNull()

            locationPoints = geocodedPoints

            // Build route through all points
            if (geocodedPoints.size >= 2) {
                val allRoutePoints = mutableListOf<LocationPoint>()

                // Get route segments between consecutive stops
                for (i in 0 until geocodedPoints.size - 1) {
                    val start = geocodedPoints[i]
                    val end = geocodedPoints[i + 1]

                    // Try OSRM first, but don't block on it
                    val segmentPoints = try {
                        locationHelper.getRoutePoints(
                            startPoint = start,
                            endPoint = end,
                            profile = "driving"
                        )
                    } catch (e: Exception) {
                        println("OSRM failed for segment $i: ${e.message}")
                        null
                    }

                    if (segmentPoints != null && segmentPoints.isNotEmpty()) {
                        // Add segment points, avoiding duplicates at connection points
                        if (allRoutePoints.isEmpty()) {
                            allRoutePoints.addAll(segmentPoints)
                        } else {
                            // Skip first point of segment as it's the same as last point of previous segment
                            allRoutePoints.addAll(segmentPoints.drop(1))
                        }
                    } else {
                        // Fallback: create simple line with interpolated points for smoother rendering
                        println("Using fallback for segment $i")
                        if (allRoutePoints.isEmpty()) {
                            allRoutePoints.add(start)
                        }

                        // Add some intermediate points for smoother line (divide segment into 3 parts)
                        val latDiff = (end.latitude - start.latitude) / 3
                        val lonDiff = (end.longitude - start.longitude) / 3

                        allRoutePoints.add(
                            LocationPoint(
                                start.latitude + latDiff,
                                start.longitude + lonDiff,
                                ""
                            )
                        )
                        allRoutePoints.add(
                            LocationPoint(
                                start.latitude + 2 * latDiff,
                                start.longitude + 2 * lonDiff,
                                ""
                            )
                        )
                        allRoutePoints.add(end)
                    }
                }

                routePoints = allRoutePoints
            }

            isLoading = false
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        "Szczegóły trasy",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Wróć",
                            tint = Color.White
                        )
                    }
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
        ) {
            // Map Card
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(300.dp)
                    .padding(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                shape = RoundedCornerShape(12.dp)
            ) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(
                            color = Color(0xFF1976D2)
                        )
                    } else if (locationPoints.isNotEmpty()) {
                        Map(
                            modifier = Modifier.fillMaxSize(),
                            initialZoom = 12.0,
                            enableMyLocation = false,
                            userMarkers = locationPoints,
                            routePoints = routePoints,
                            onMapReady = { }
                        )
                    } else {
                        Text(
                            text = "Nie udało się załadować mapy",
                            color = Color(0xFF757575)
                        )
                    }
                }
            }

            // Route Summary Card
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                shape = RoundedCornerShape(12.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceAround
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "Całkowity czas",
                            fontSize = 12.sp,
                            color = Color(0xFF757575)
                        )
                        val totalDuration = Duration.between(
                            destinationPoints.first().arrivalTime,
                            destinationPoints.last().arrivalTime
                        )
                        val hours = totalDuration.toHours()
                        val minutes = totalDuration.toMinutes() % 60
                        Text(
                            text = if (hours > 0) "${hours}h ${minutes}min" else "${minutes}min",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1976D2)
                        )
                    }

                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "Przystanki",
                            fontSize = 12.sp,
                            color = Color(0xFF757575)
                        )
                        Text(
                            text = "${destinationPoints.size}",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1976D2)
                        )
                    }

                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "Przyjazd",
                            fontSize = 12.sp,
                            color = Color(0xFF757575)
                        )
                        Text(
                            text = destinationPoints.last().arrivalTime
                                .atZone(java.time.ZoneId.systemDefault())
                                .format(timeFormatter),
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1976D2)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Stops List
            Text(
                text = "Przystanki po drodze",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(horizontal = 16.dp),
                color = Color(0xFF212121)
            )

            Spacer(modifier = Modifier.height(8.dp))

            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                itemsIndexed(destinationPoints) { index, point ->
                    StopItem(
                        destinationPoint = point,
                        isFirst = index == 0,
                        isLast = index == destinationPoints.size - 1,
                        timeFormatter = timeFormatter
                    )
                }

                // Add bottom spacing
                item {
                    Spacer(modifier = Modifier.height(16.dp))
                }
            }
        }
    }
}

@Composable
fun StopItem(
    destinationPoint: DestinationPoint,
    isFirst: Boolean,
    isLast: Boolean,
    timeFormatter: DateTimeFormatter
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isFirst || isLast) Color(0xFFF5F5F5) else Color.White
        ),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Stop indicator
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(
                        when {
                            isFirst -> Color(0xFF4CAF50)
                            isLast -> Color(0xFFF44336)
                            else -> Color(0xFF2196F3)
                        }
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.Place,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(24.dp)
                )
            }

            Spacer(modifier = Modifier.width(16.dp))

            // Stop info
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = destinationPoint.name,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF212121)
                )
                if (isFirst) {
                    Text(
                        text = "Punkt startowy",
                        fontSize = 12.sp,
                        color = Color(0xFF4CAF50)
                    )
                } else if (isLast) {
                    Text(
                        text = "Punkt docelowy",
                        fontSize = 12.sp,
                        color = Color(0xFFF44336)
                    )
                }
            }

            // Arrival time
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = destinationPoint.arrivalTime
                        .atZone(java.time.ZoneId.systemDefault())
                        .format(timeFormatter),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1976D2)
                )
                if (!isFirst) {
                    Text(
                        text = "Przyjazd",
                        fontSize = 12.sp,
                        color = Color(0xFF757575)
                    )
                }
            }
        }
    }
}
