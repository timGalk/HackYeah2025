package com.edu.hackyeah.location

/**
 * Prosta reprezentacja punktu incydentu do wyświetlenia na mapie.
 */
data class IncidentPoint(
    val latitude: Double,
    val longitude: Double,
    val category: String? = null,
    val description: String? = null
)

