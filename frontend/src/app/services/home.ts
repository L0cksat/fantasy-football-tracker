import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { HomePage } from '../models/tracker';

@Injectable({
  providedIn: 'root',
})
export class HomeService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://localhost:8080/api/v1/home';

  getHome(): Observable<HomePage> {
    return this.http.get<HomePage>(this.apiUrl);
  }
}
