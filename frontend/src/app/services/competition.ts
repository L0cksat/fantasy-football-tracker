import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { CompareView, Competition, TeamView, TotalsView } from '../models/tracker';

@Injectable({
  providedIn: 'root',
})
export class CompetitionService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://localhost:8080/api/v1/competitions';

  getCompetitions(): Observable<Competition[]> {
    return this.http.get<Competition[]>(this.apiUrl);
  }

  getTeam(id: number, gameweek?: number): Observable<TeamView> {
    const options = gameweek != null ? { params: { gameweek } } : {};
    return this.http.get<TeamView>(`${this.apiUrl}/${id}/team`, options);
  }

  getGameweek(id: number, n: number): Observable<TeamView> {
    return this.http.get<TeamView>(`${this.apiUrl}/${id}/gameweeks/${n}`);
  }

  compare(id: number, from: number, to: number): Observable<CompareView> {
    return this.http.get<CompareView>(`${this.apiUrl}/${id}/compare`, {
      params: { from, to },
    });
  }

  totals(id: number): Observable<TotalsView> {
    return this.http.get<TotalsView>(`${this.apiUrl}/${id}/totals`);
  }
}
