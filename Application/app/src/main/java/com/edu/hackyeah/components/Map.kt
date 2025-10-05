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
import androidx.core.content.ContextCompat
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
import com.edu.hackyeah.R
import com.edu.hackyeah.location.IncidentPoint

@Composable
fun Map(
    modifier: Modifier = Modifier,
    initialZoom: Double = 15.0,
    enableMyLocation: Boolean = true,
    userMarkers: List<LocationPoint> = emptyList(),
    defaultRoutePoints: List<LocationPoint> = emptyList(),
    suggestedRoutePoints: List<LocationPoint> = emptyList(),
    incidentPoints: List<IncidentPoint> = emptyList(),
    onMapReady: ((MapView) -> Unit)? = null
) {
    val context = LocalContext.current

    val mapView = rememberMapViewWithLifecycle(context)

    LaunchedEffect(userMarkers, defaultRoutePoints, suggestedRoutePoints, incidentPoints) {
        mapView.overlays.removeAll { it is Marker || it is Polyline }

        // Draw suggested route (green)
        if (suggestedRoutePoints.size >= 2) {
            val polyline = Polyline().apply {
                outlinePaint.color = "#4CAF50".toColorInt() // Green
                outlinePaint.strokeWidth = 12f
                outlinePaint.strokeCap = android.graphics.Paint.Cap.ROUND
                setPoints(suggestedRoutePoints.map { GeoPoint(it.latitude, it.longitude) })
            }
            mapView.overlays.add(polyline)
        }

        // Draw default route (blue or red if no suggestion)
        if (defaultRoutePoints.size >= 2) {
            val polyline = Polyline().apply {
                val color = if (suggestedRoutePoints.isNotEmpty()) "#F44336".toColorInt() else "#1976D2".toColorInt() // Red if suggested, else blue
                outlinePaint.color = color
                outlinePaint.strokeWidth = if (suggestedRoutePoints.isNotEmpty()) 8f else 10f
                outlinePaint.strokeCap = android.graphics.Paint.Cap.ROUND
                setPoints(defaultRoutePoints.map { GeoPoint(it.latitude, it.longitude) })
            }
            mapView.overlays.add(polyline)
        }

        // Add markers for user-specified points (start/end)
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
                }
                mapView.overlays.add(marker)
            }
        }

        // Add markers for incidents
        incidentPoints.forEach { incident ->
            val marker = Marker(mapView).apply {
                position = GeoPoint(incident.latitude, incident.longitude)
                setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
                title = incident.category ?: "Incydent"
                snippet = incident.description
                // Użyj niestandardowej ikony dla incydentów
                icon = ContextCompat.getDrawable(context, R.drawable.ic_launcher_background)
            }
            mapView.overlays.add(marker)
        }


        // Zoom to show all points
        val allPoints = (userMarkers + defaultRoutePoints + suggestedRoutePoints).distinct()
        if (allPoints.size >= 2) {
            val bounds = org.osmdroid.util.BoundingBox.fromGeoPoints(allPoints.map { GeoPoint(it.latitude, it.longitude) })
            Handler(Looper.getMainLooper()).post {
                mapView.zoomToBoundingBox(bounds, true, 100)
            }
        } else if (allPoints.size == 1) {
            Handler(Looper.getMainLooper()).post {
                mapView.controller.animateTo(GeoPoint(allPoints[0].latitude, allPoints[0].longitude))
                mapView.controller.setZoom(15.0)
            }
        }

        mapView.invalidate()
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
