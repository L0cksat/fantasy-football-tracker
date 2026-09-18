package com.fantasytracker.backend.controllers;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.fantasytracker.backend.dto.HomePageResponse;
import com.fantasytracker.backend.services.HomePageService;

@RestController
@RequestMapping("/api/v1/home")
public class HomeController {

	private final HomePageService homePageService;

	public HomeController(HomePageService homePageService) {
		this.homePageService = homePageService;
	}

	@GetMapping
	public ResponseEntity<HomePageResponse> home() {
		return ResponseEntity.ok(homePageService.homePage());
	}
}
