package com.edu.hackyeah.location

import java.time.Instant

data class DestinationPoint(
    val name: String,
    val arrivalTime: Instant,
    val routeNumber: String? = null
)