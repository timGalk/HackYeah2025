package com.edu.hackyeah.location

import android.annotation.SuppressLint
import android.content.Context
import android.location.Address
import android.location.Geocoder
import android.os.Looper
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.edu.hackyeah.network.IncidentService
import com.edu.hackyeah.network.RoutingService
import com.edu.hackyeah.network.TransportPath
import com.edu.hackyeah.network.TransportRouteService
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import java.time.Instant
import java.util.Locale
import kotlin.coroutines.resume

data class LocationPoint(
    val latitude: Double,
    val longitude: Double,
    val address: String
)

class LocationHelper(private val context: Context) {

    private val fusedLocationClient: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(context)

    init {
        // Load stop name mappings from assets
        try {
            val json = context.assets.open("node_name_mapping.json").bufferedReader().use { it.readText() }
            TransportRouteService.loadStopMappings(json)
            println("Successfully loaded stop mappings from assets")
        } catch (e: Exception) {
            println("Error loading stop mappings: ${e.message}")
            e.printStackTrace()
        }
    }

    fun getAllStopNames(): List<String> {
        return try {
            val reverseJson = context.assets.open("node_name_mapping_reverse.json").bufferedReader().use { it.readText() }
            val gson = com.google.gson.Gson()
            val type = object : com.google.gson.reflect.TypeToken<Map<String, String>>() {}.type
            val reverseMapping: Map<String, String> = gson.fromJson(reverseJson, type)
            reverseMapping.keys.sorted()
        } catch (e: Exception) {
            println("Error loading stop names: ${e.message}")
            emptyList()
        }
    }

    @SuppressLint("MissingPermission")
    suspend fun getCurrentAddress(): String? {
        val location = getCurrentLocationInternal() ?: return null

        return try {
            suspendCancellableCoroutine { continuation ->
                val geocoder = Geocoder(context, Locale.getDefault())
                geocoder.getFromLocation(
                    location.latitude,
                    location.longitude,
                    1
                ) { addresses ->
                    val address = addresses.firstOrNull()
                    val result = buildAddressString(address)
                    continuation.resume(result)
                }
            }
        } catch (e: Exception) {
            null
        }
    }

    @SuppressLint("MissingPermission")
    suspend fun getCurrentLocation(): LocationPoint? {
        val location = getCurrentLocationInternal() ?: return null

        return LocationPoint(
            latitude = location.latitude,
            longitude = location.longitude,
            address = ""
        )
    }

    @SuppressLint("MissingPermission")
    private suspend fun getCurrentLocationInternal(): android.location.Location? {
        // Najpierw spróbuj pobrać ostatnią znaną lokalizację
        val lastLocation = withTimeoutOrNull(2000) {
            suspendCancellableCoroutine { continuation ->
                fusedLocationClient.lastLocation
                    .addOnSuccessListener { location ->
                        continuation.resume(location)
                    }
                    .addOnFailureListener {
                        continuation.resume(null)
                    }
            }
        }

        // Jeśli lastLocation istnieje i nie jest zbyt stara, użyj jej
        if (lastLocation != null && System.currentTimeMillis() - lastLocation.time < 60000) {
            return lastLocation
        }

        // W przeciwnym razie żądaj nowej lokalizacji
        return withTimeoutOrNull(10000) {
            suspendCancellableCoroutine { continuation ->
                val locationRequest = LocationRequest.Builder(
                    Priority.PRIORITY_HIGH_ACCURACY,
                    5000
                ).apply {
                    setMaxUpdates(1)
                    setWaitForAccurateLocation(false)
                }.build()

                val locationCallback = object : LocationCallback() {
                    override fun onLocationResult(locationResult: LocationResult) {
                        val location = locationResult.lastLocation
                        fusedLocationClient.removeLocationUpdates(this)
                        continuation.resume(location)
                    }
                }

                continuation.invokeOnCancellation {
                    fusedLocationClient.removeLocationUpdates(locationCallback)
                }

                fusedLocationClient.requestLocationUpdates(
                    locationRequest,
                    locationCallback,
                    Looper.getMainLooper()
                )
            }
        }
    }

    suspend fun getCoordinatesFromAddress(addressString: String): LocationPoint? = suspendCancellableCoroutine { continuation ->
        if (addressString.isBlank()) {
            continuation.resume(null)
            return@suspendCancellableCoroutine
        }

        val geocoder = Geocoder(context, Locale.getDefault())

        geocoder.getFromLocationName(addressString, 1) { addresses ->
            val address = addresses.firstOrNull()
            val result = address?.let {
                LocationPoint(
                    latitude = it.latitude,
                    longitude = it.longitude,
                    address = addressString
                )
            }
            continuation.resume(result)
        }
    }

    suspend fun getRoutePoints(
        startPoint: LocationPoint,
        endPoint: LocationPoint,
        profile: String = "driving" // driving, walking, cycling
    ): List<LocationPoint>? {
        return try {
            val points = RoutingService.getRoutePoints(
                startPoint.latitude,
                startPoint.longitude,
                endPoint.latitude,
                endPoint.longitude,
                profile
            )

            points?.map { (lat, lon) ->
                LocationPoint(
                    latitude = lat,
                    longitude = lon,
                    address = ""
                )
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    suspend fun getTransportRoute(
        sourceAddress: String,
        targetAddress: String
    ): TransportRouteResult? {
        return try {
            println("Searching route from: $sourceAddress to: $targetAddress")

            val sourceStopId = findNearestStopId(sourceAddress)
            val targetStopId = findNearestStopId(targetAddress)

            println("Found stop IDs: source=$sourceStopId, target=$targetStopId")

            if (sourceStopId == null || targetStopId == null) {
                println("Could not find stop IDs for addresses")
                return null
            }

            val response = TransportRouteService.getTransportRoute(
                mode = "bus",
                sourceStopId = sourceStopId,
                targetStopId = targetStopId
            ) ?: return null

            println("Got response from API: incident=${response.incidentDetected}")

            val defaultPathPoints = response.defaultPath?.let { path ->
                convertPathToDestinationPoints(path)
            } ?: emptyList()

            val suggestedPathPoints = response.suggestedPath?.let { path ->
                convertPathToDestinationPoints(path)
            }

            val incidents = fetchIncidentsForPath(response.defaultPath)


            TransportRouteResult(
                defaultPath = defaultPathPoints,
                suggestedPath = suggestedPathPoints,
                incidentDetected = response.incidentDetected,
                message = response.message,
                incidents = incidents
            )
        } catch (e: Exception) {
            println("Error getting transport route: ${e.message}")
            e.printStackTrace()
            null
        }
    }

    private fun convertPathToDestinationPoints(path: TransportPath): List<DestinationPoint> {
        val destinationPoints = mutableListOf<DestinationPoint>()
        var currentTime = Instant.now()
        val firstStopName = TransportRouteService.getStopName(path.nodes.first())
        destinationPoints.add(
            DestinationPoint(
                name = firstStopName,
                arrivalTime = currentTime
            )
        )
        val processedStops = mutableSetOf(path.nodes.first())
        for ((index, segment) in path.segments.withIndex()) {
            currentTime = currentTime.plusSeconds(segment.currentWeight.toLong())
            val targetStopName = TransportRouteService.getStopName(segment.target)
            if (!processedStops.contains(segment.target)) {
                destinationPoints.add(
                    DestinationPoint(
                        name = targetStopName,
                        arrivalTime = currentTime,
                        routeNumber = segment.metadata?.routeShortName
                    )
                )
                processedStops.add(segment.target)
            }
        }
        return destinationPoints
    }


    private suspend fun fetchIncidentsForPath(path: TransportPath?): List<IncidentPoint> {
        if (path == null) return emptyList()

        val stopIds = path.segments.filter { it.impacted }.map { it.source }
        if (stopIds.isEmpty()) return emptyList()

        return try {
            val allIncidents = IncidentService.fetchAllIncidents().getOrNull() ?: emptyList()
            val stopCoordinates = coroutineScope {
                stopIds.map { stopId ->
                    async {
                        val stopName = TransportRouteService.getStopName(stopId)
                        getCoordinatesFromAddress(stopName)
                    }
                }.awaitAll().filterNotNull()
            }

            // Prosta logika dopasowania - w świecie rzeczywistym potrzebowalibyśmy lepszego sposobu
            // aby powiązać incydenty z segmentami trasy.
            // Tutaj po prostu filtrujemy incydenty, które są blisko współrzędnych przystanków, na które wpłynęły.
            val incidentPoints = mutableListOf<IncidentPoint>()
            val threshold = 0.01 // ok. 1km

            for (incident in allIncidents) {
                if (incident.latitude != null && incident.longitude != null) {
                    for (coord in stopCoordinates) {
                        if (kotlin.math.abs(incident.latitude - coord.latitude) < threshold &&
                            kotlin.math.abs(incident.longitude - coord.longitude) < threshold
                        ) {
                            incidentPoints.add(
                                IncidentPoint(
                                    latitude = incident.latitude,
                                    longitude = incident.longitude,
                                    category = incident.category,
                                    description = incident.description
                                )
                            )
                            break
                        }
                    }
                }
            }
            incidentPoints
        } catch (e: Exception) {
            println("Error fetching incidents for path: ${e.message}")
            emptyList()
        }
    }

    private suspend fun findNearestStopId(address: String): String? {
        // For now, we'll need to load the reverse mapping to find stops by name
        // This is a simplified version - in production you'd want to use geocoding + nearest stop lookup
        return try {
            val reverseJson = context.assets.open("node_name_mapping_reverse.json").bufferedReader().use { it.readText() }
            val gson = com.google.gson.Gson()
            val type = object : com.google.gson.reflect.TypeToken<Map<String, String>>() {}.type
            val reverseMapping: Map<String, String> = gson.fromJson(reverseJson, type)

            // Try to find exact match first
            reverseMapping[address] ?: run {
                // Try partial match
                reverseMapping.entries.find { it.key.contains(address, ignoreCase = true) }?.value
            }
        } catch (e: Exception) {
            println("Error finding stop ID: ${e.message}")
            null
        }
    }

    private fun buildAddressString(address: Address?): String? {
        if (address == null) return null

        val city = address.locality ?: address.subAdminArea
        val street = buildString {
            address.thoroughfare?.let { append(it) }
            address.subThoroughfare?.let {
                if (isNotEmpty()) append(" ")
                append(it)
            }
        }.ifEmpty { null }

        return buildString {
            street?.let { append(it) }
            city?.let {
                if (isNotEmpty()) append(", ")
                append(it)
            }
        }.ifEmpty { null }
    }
}

data class TransportRouteResult(
    val defaultPath: List<DestinationPoint>,
    val suggestedPath: List<DestinationPoint>?,
    val incidentDetected: Boolean,
    val message: String?,
    val incidents: List<IncidentPoint>
)
