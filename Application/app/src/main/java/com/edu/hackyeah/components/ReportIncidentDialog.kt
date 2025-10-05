package com.edu.hackyeah.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.edu.hackyeah.location.LocationHelper
import com.edu.hackyeah.network.IncidentService
import kotlinx.coroutines.launch
import androidx.compose.runtime.livedata.observeAsState
import androidx.lifecycle.viewmodel.compose.viewModel
import com.edu.hackyeah.Auth.ViewModel.AuthState
import com.edu.hackyeah.Auth.ViewModel.AuthViewModel

enum class IncidentCategory(val displayName: String, val apiValue: String) {
    WYPADEK_DROGOWY("Wypadek drogowy", "wypadek_drogowy"),
    KOREK("Korek", "korek"),
    POTRACENIE("Potrącenie", "potracenie")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportIncidentDialog(
    onDismiss: () -> Unit,
    onSuccess: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var description by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf<IncidentCategory?>(null) }
    var expandedCategory by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var successMessage by remember { mutableStateOf<String?>(null) }

    // Observe authentication state (do NOT disable button because we want to show validation errors)
    val authViewModel: AuthViewModel = viewModel()
    val authState by authViewModel.authState.observeAsState(AuthState.Unauthenticated)
    val userEmail by authViewModel.userProfile.observeAsState(null)

    Dialog(onDismissRequest = onDismiss) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(24.dp)
            ) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        "Zgłoś incydent",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1976D2)
                    )
                    IconButton(onClick = onDismiss) {
                        Icon(
                            Icons.Default.Close,
                            contentDescription = "Zamknij",
                            tint = Color.Gray
                        )
                    }
                }

                // Show info when user is not authenticated
                if (authState !is AuthState.Authenticated) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Musisz być zalogowany, aby zgłosić incydent",
                        fontSize = 12.sp,
                        color = Color(0xFFD32F2F)
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Category Dropdown
                Text(
                    "Kategoria *",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color.Gray
                )
                Spacer(modifier = Modifier.height(8.dp))
                ExposedDropdownMenuBox(
                    expanded = expandedCategory,
                    onExpandedChange = { expandedCategory = !expandedCategory }
                ) {
                    OutlinedTextField(
                        value = selectedCategory?.displayName ?: "",
                        onValueChange = {},
                        readOnly = true,
                        placeholder = { Text("Wybierz kategorię") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expandedCategory) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor(MenuAnchorType.PrimaryNotEditable),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Color(0xFF1976D2),
                            unfocusedBorderColor = Color.LightGray
                        )
                    )
                    ExposedDropdownMenu(
                        expanded = expandedCategory,
                        onDismissRequest = { expandedCategory = false }
                    ) {
                        IncidentCategory.entries.forEach { category ->
                            DropdownMenuItem(
                                text = { Text(category.displayName) },
                                onClick = {
                                    selectedCategory = category
                                    expandedCategory = false
                                }
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Description
                Text(
                    "Opis *",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color.Gray
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    placeholder = { Text("Opisz szczegóły incydentu...") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(120.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Color(0xFF1976D2),
                        unfocusedBorderColor = Color.LightGray
                    ),
                    maxLines = 5
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Info text
                Text(
                    "Twoja lokalizacja zostanie automatycznie dodana",
                    fontSize = 12.sp,
                    color = Color.Gray,
                    modifier = Modifier.padding(start = 4.dp)
                )

                // Error message
                errorMessage?.let {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        it,
                        fontSize = 12.sp,
                        color = Color.Red,
                        modifier = Modifier.padding(start = 4.dp)
                    )
                }

                // Success message
                successMessage?.let {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        it,
                        fontSize = 12.sp,
                        color = Color(0xFF4CAF50),
                        modifier = Modifier.padding(start = 4.dp)
                    )
                }

                Spacer(modifier = Modifier.height(24.dp))

                // Submit button
                Button(
                    onClick = {
                        if (authState !is AuthState.Authenticated) {
                            errorMessage = "Musisz być zalogowany, aby zgłosić incydent"
                            return@Button
                        }
                        if (selectedCategory == null) {
                            errorMessage = "Wybierz kategorię"
                            return@Button
                        }
                        if (description.isBlank()) {
                            errorMessage = "Wpisz opis incydentu"
                            return@Button
                        }

                        errorMessage = null
                        isLoading = true

                        scope.launch {
                            try {
                                val locationHelper = LocationHelper(context)
                                val location = locationHelper.getCurrentLocation()

                                if (location == null) {
                                    errorMessage = "Nie można pobrać lokalizacji"
                                    isLoading = false
                                    return@launch
                                }

                                val result = IncidentService.reportIncident(
                                    latitude = location.latitude,
                                    longitude = location.longitude,
                                    description = description,
                                    category = selectedCategory!!.apiValue,
                                    username = userEmail.toString()

                                )

                                isLoading = false

                                result.onSuccess {
                                    successMessage = "Incydent zgłoszony pomyślnie!"
                                    kotlinx.coroutines.delay(1500)
                                    onSuccess()
                                    onDismiss()
                                }.onFailure { e ->
                                    errorMessage = "Błąd: ${e.message}"
                                }
                            } catch (e: Exception) {
                                isLoading = false
                                errorMessage = "Wystąpił błąd: ${e.message}"
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFF1976D2)
                    ),
                    enabled = !isLoading,
                    shape = RoundedCornerShape(8.dp)
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            color = Color.White,
                            strokeWidth = 2.dp
                        )
                    } else {
                        Text(
                            "Zgłoś incydent",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Cancel button
                TextButton(
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !isLoading
                ) {
                    Text(
                        "Anuluj",
                        color = Color.Gray
                    )
                }
            }
        }
    }
}
