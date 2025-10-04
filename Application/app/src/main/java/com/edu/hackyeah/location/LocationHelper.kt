package com.edu.hackyeah.location

import android.annotation.SuppressLint
import android.content.Context
import android.location.Address
import android.location.Geocoder
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import com.edu.hackyeah.network.RoutingService
import kotlinx.coroutines.suspendCancellableCoroutine
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

    @SuppressLint("MissingPermission")
    suspend fun getCurrentAddress(): String? = suspendCancellableCoroutine { continuation ->
        fusedLocationClient.lastLocation.addOnSuccessListener { location ->
            if (location != null) {
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
            } else {
                continuation.resume(null)
            }
        }.addOnFailureListener {
            continuation.resume(null)
        }
    }

    @SuppressLint("MissingPermission")
    suspend fun getCurrentLocation(): LocationPoint? = suspendCancellableCoroutine { continuation ->
        fusedLocationClient.lastLocation.addOnSuccessListener { location ->
            if (location != null) {
                continuation.resume(
                    LocationPoint(
                        latitude = location.latitude,
                        longitude = location.longitude,
                        address = ""
                    )
                )
            } else {
                continuation.resume(null)
            }
        }.addOnFailureListener {
            continuation.resume(null)
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
