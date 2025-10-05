package com.edu.hackyeah.components

import android.content.Context
import android.os.Handler
import android.os.Looper
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import com.edu.hackyeah.location.LocationPoint
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polyline
import org.osmdroid.views.overlay.mylocation.GpsMyLocationProvider
import org.osmdroid.views.overlay.mylocation.MyLocationNewOverlay
import androidx.core.graphics.toColorInt

@Composable
fun Map(
    modifier: Modifier = Modifier,
    initialZoom: Double = 15.0,
    enableMyLocation: Boolean = true,
    userMarkers: List<LocationPoint> = emptyList(),
    routePoints: List<LocationPoint> = emptyList(),
    onMapReady: ((MapView) -> Unit)? = null
) {
    val context = LocalContext.current

    val mapView = rememberMapViewWithLifecycle(context)

    LaunchedEffect(userMarkers, routePoints) {
        if (userMarkers.isNotEmpty() || routePoints.isNotEmpty()) {
            mapView.overlays.removeAll { it is Marker || it is Polyline }

            // Only draw polyline if routePoints are explicitly provided
            if (routePoints.isNotEmpty() && routePoints.size >= 2) {
                val polyline = Polyline().apply {
                    outlinePaint.color = "#1976D2".toColorInt()
                    outlinePaint.strokeWidth = 10f
                    outlinePaint.strokeCap = android.graphics.Paint.Cap.ROUND
                    outlinePaint.strokeJoin = android.graphics.Paint.Join.ROUND

                    // Add all points to the polyline
                    val geoPoints = routePoints.map { GeoPoint(it.latitude, it.longitude) }
                    setPoints(geoPoints)
                }
                mapView.overlays.add(polyline)
            }

            // Add markers ONLY for user-specified points
            if (userMarkers.isNotEmpty()) {
                userMarkers.forEachIndexed { index, point ->
                    val marker = Marker(mapView).apply {
                        position = GeoPoint(point.latitude, point.longitude)
                        setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                        title = point.address.ifEmpty {
                            when (index) {
                                0 -> "Start"
                                userMarkers.size - 1 -> "Destination"
                                else -> "Waypoint $index"
                            }
                        }
                        snippet = when (index) {
                            0 -> "Starting point"
                            userMarkers.size - 1 -> "End point"
                            else -> "Stop $index"
                        }
                    }
                    mapView.overlays.add(marker)
                }
            }

            // Zoom to show all markers
            val pointsForZoom = if (routePoints.isNotEmpty()) routePoints else userMarkers

            if (pointsForZoom.size >= 2) {
                val latitudes = pointsForZoom.map { it.latitude }
                val longitudes = pointsForZoom.map { it.longitude }

                val bounds = org.osmdroid.util.BoundingBox(
                    latitudes.maxOrNull() ?: 0.0,
                    longitudes.maxOrNull() ?: 0.0,
                    latitudes.minOrNull() ?: 0.0,
                    longitudes.minOrNull() ?: 0.0
                )
                Handler(Looper.getMainLooper()).post {
                    mapView.zoomToBoundingBox(bounds, true, 100)
                }
            } else if (pointsForZoom.size == 1) {
                Handler(Looper.getMainLooper()).post {
                    mapView.controller.animateTo(GeoPoint(pointsForZoom[0].latitude, pointsForZoom[0].longitude))
                    mapView.controller.setZoom(15.0)
                }
            }

            mapView.invalidate()
        }
    }

    AndroidView(
        modifier = modifier.fillMaxSize(),
        factory = {
            mapView.apply {
                setTileSource(TileSourceFactory.MAPNIK)
                setMultiTouchControls(true)
                controller.setZoom(initialZoom)

                if (enableMyLocation) {
                    val locationOverlay = MyLocationNewOverlay(GpsMyLocationProvider(context), this)
                    locationOverlay.enableMyLocation()
                    locationOverlay.enableFollowLocation()
                    locationOverlay.isDrawAccuracyEnabled = true

                    locationOverlay.runOnFirstFix {
                        Handler(Looper.getMainLooper()).post {
                            controller.setCenter(locationOverlay.myLocation)
                            controller.animateTo(locationOverlay.myLocation)
                        }
                    }

                    overlays.add(locationOverlay)
                }

                onMapReady?.invoke(this)
            }
        }
    )

    DisposableEffect(Unit) {
        onDispose {
            mapView.onDetach()
        }
    }
}

@Composable
private fun rememberMapViewWithLifecycle(context: Context): MapView {
    return remember {
        Configuration.getInstance().load(
            context,
            context.getSharedPreferences("osmdroid", Context.MODE_PRIVATE)
        )
        MapView(context)
    }
}