package com.edu.hackyeah.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Popup

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AutocompleteStopField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    availableStops: List<String>,
    leadingIcon: @Composable (() -> Unit)? = null,
    trailingIcon: @Composable (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }
    
    // Filter stops based on input
    val filteredStops = remember(value, availableStops) {
        if (value.length >= 2) {
            availableStops.filter { 
                it.contains(value, ignoreCase = true) 
            }.take(10) // Limit to 10 suggestions
        } else {
            emptyList()
        }
    }

    Column(modifier = modifier) {
        OutlinedTextField(
            value = value,
            onValueChange = { newValue ->
                onValueChange(newValue)
                expanded = newValue.isNotEmpty() && filteredStops.isNotEmpty()
            },
            placeholder = {
                Text(
                    placeholder,
                    fontSize = 14.sp,
                    color = Color(0xFF999999)
                )
            },
            modifier = Modifier.fillMaxWidth(),
            leadingIcon = leadingIcon,
            trailingIcon = trailingIcon,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = Color(0xFF1976D2),
                unfocusedBorderColor = Color(0xFFE0E0E0),
                focusedContainerColor = Color(0xFFF8F9FA),
                unfocusedContainerColor = Color.White
            ),
            shape = RoundedCornerShape(12.dp)
        )

        // Dropdown suggestions
        if (expanded && filteredStops.isNotEmpty()) {
            Popup(
                onDismissRequest = { expanded = false }
            ) {
                Surface(
                    modifier = Modifier
                        .fillMaxWidth(0.9f)
                        .heightIn(max = 300.dp),
                    shape = RoundedCornerShape(12.dp),
                    shadowElevation = 8.dp,
                    color = Color.White
                ) {
                    LazyColumn {
                        items(filteredStops) { stop ->
                            ListItem(
                                headlineContent = {
                                    Text(
                                        stop,
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Medium
                                    )
                                },
                                leadingContent = {
                                    Icon(
                                        Icons.Default.Place,
                                        contentDescription = null,
                                        tint = Color(0xFF1976D2)
                                    )
                                },
                                modifier = Modifier.clickable {
                                    onValueChange(stop)
                                    expanded = false
                                },
                                colors = ListItemDefaults.colors(
                                    containerColor = Color.White
                                )
                            )
                        }
                    }
                }
            }
        }
    }
}

