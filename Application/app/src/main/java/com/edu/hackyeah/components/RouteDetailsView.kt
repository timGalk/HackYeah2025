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
import androidx.compose.material3.Text
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
import com.edu.hackyeah.location.TransportRouteResult
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import java.time.Duration
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RouteDetailsView(
    routeResult: TransportRouteResult,
    onBackClick: () -> Unit
) {
    val timeFormatter = DateTimeFormatter.ofPattern("HH:mm")
    val context = LocalContext.current
    val locationHelper = remember { LocationHelper(context) }

    var defaultLocationPoints by remember { mutableStateOf<List<LocationPoint>>(emptyList()) }
    var suggestedLocationPoints by remember { mutableStateOf<List<LocationPoint>>(emptyList()) }
    var defaultRoutePoints by remember { mutableStateOf<List<LocationPoint>>(emptyList()) }
    var suggestedRoutePoints by remember { mutableStateOf<List<LocationPoint>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    // Fetch geolocation for all stops and build routes
    LaunchedEffect(routeResult) {
        isLoading = true

        coroutineScope {
            // Geocode points for default path
            val geocodedDefaultPoints = routeResult.defaultPath.map { point ->
                async { locationHelper.getCoordinatesFromAddress(point.name) }
            }.awaitAll().filterNotNull()
            defaultLocationPoints = geocodedDefaultPoints

            // Geocode points for suggested path
            val geocodedSuggestedPoints = routeResult.suggestedPath?.map { point ->
                async { locationHelper.getCoordinatesFromAddress(point.name) }
            }?.awaitAll()?.filterNotNull() ?: emptyList()
            suggestedLocationPoints = geocodedSuggestedPoints

            // Build route for default path
            if (geocodedDefaultPoints.size >= 2) {
                defaultRoutePoints = buildRoute(geocodedDefaultPoints, locationHelper)
            }

            // Build route for suggested path
            if (geocodedSuggestedPoints.size >= 2) {
                suggestedRoutePoints = buildRoute(geocodedSuggestedPoints, locationHelper)
            }

            isLoading = false
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF5F5F5))
    ) {
        // Back button
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            IconButton(
                onClick = onBackClick,
                modifier = Modifier.align(Alignment.CenterStart)
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Wróć",
                    tint = Color(0xFF1976D2),
                    modifier = Modifier.size(28.dp)
                )
            }
        }

        // Map Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .height(300.dp)
                .padding(horizontal = 16.dp),
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
                } else if (defaultLocationPoints.isNotEmpty()) {
                    Map(
                        modifier = Modifier.fillMaxSize(),
                        initialZoom = 12.0,
                        enableMyLocation = false,
                        userMarkers = listOfNotNull(defaultLocationPoints.firstOrNull(), defaultLocationPoints.lastOrNull()),
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
                        routeResult.defaultPath.first().arrivalTime,
                        routeResult.defaultPath.last().arrivalTime
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
                        text = "${routeResult.defaultPath.size}",
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
                        text = routeResult.defaultPath.last().arrivalTime
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
            itemsIndexed(routeResult.defaultPath) { index, point ->
                StopItem(
                    destinationPoint = point,
                    isFirst = index == 0,
                    isLast = index == routeResult.defaultPath.size - 1,
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

private suspend fun buildRoute(points: List<LocationPoint>, locationHelper: LocationHelper): List<LocationPoint> {
    val allRoutePoints = mutableListOf<LocationPoint>()
    if (points.size < 2) return emptyList()

    for (i in 0 until points.size - 1) {
        val start = points[i]
        val end = points[i + 1]
        val segmentPoints = locationHelper.getRoutePoints(start, end)
        if (segmentPoints != null && segmentPoints.isNotEmpty()) {
            if (allRoutePoints.isEmpty()) {
                allRoutePoints.addAll(segmentPoints)
            } else {
                allRoutePoints.addAll(segmentPoints.drop(1))
            }
        } else {
            if (allRoutePoints.isEmpty()) allRoutePoints.add(start)
            allRoutePoints.add(end)
        }
    }
    return allRoutePoints
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
                } else if (destinationPoint.routeNumber != null) {
                    Text(
                        text = "Linia ${destinationPoint.routeNumber}",
                        fontSize = 12.sp,
                        color = Color(0xFF1976D2),
                        fontWeight = FontWeight.Medium
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
