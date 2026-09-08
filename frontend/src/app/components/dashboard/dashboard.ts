import { DecimalPipe, NgClass } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CompareView, Competition, TeamView, TotalsView } from '../../models/tracker';
import { CompetitionService } from '../../services/competition';

@Component({
  selector: 'app-dashboard',
  imports: [DecimalPipe, FormsModule, NgClass],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class DashboardComponent {
  private readonly competitionService = inject(CompetitionService);

  readonly competitions = signal<Competition[]>([]);
  readonly selectedId = signal<number | null>(null);
  readonly gameweek = signal<number | null>(null);
  readonly fromGw = signal(1);
  readonly toGw = signal(2);
  readonly teamView = signal<TeamView | null>(null);
  readonly compareView = signal<CompareView | null>(null);
  readonly totalsView = signal<TotalsView | null>(null);
  readonly error = signal<string | null>(null);
  readonly loading = signal(true);

  readonly selectedCompetition = computed(() =>
    this.competitions().find((item) => item.id === this.selectedId()) ?? null,
  );

  readonly pageBrand = computed(() => {
    const selected = this.selectedCompetition();
    const teamComp = this.teamView()?.competition;
    const primary = selected?.primaryColor ?? teamComp?.primaryColor ?? null;
    const secondary = selected?.secondaryColor ?? teamComp?.secondaryColor ?? null;
    if (!primary || !secondary) {
      return null;
    }
    return {
      primary,
      secondary,
      logoUrl: selected?.logoDarkUrl ?? selected?.logoUrl ?? teamComp?.logoDarkUrl ?? teamComp?.logoUrl ?? null,
    };
  });

  readonly starters = computed(() =>
    (this.teamView()?.picks ?? []).filter((pick) => pick.role === 'starter'),
  );
  readonly bench = computed(() =>
    (this.teamView()?.picks ?? []).filter((pick) => pick.role !== 'starter'),
  );

  constructor() {
    this.competitionService.getCompetitions().subscribe({
      next: (competitions) => {
        this.competitions.set(competitions);
        this.loading.set(false);
        if (competitions.length > 0) {
          this.selectCompetition(competitions[0].id);
        }
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Could not reach the backend on http://localhost:8080');
      },
    });
  }

  selectCompetition(id: number): void {
    const competition = this.competitions().find((item) => item.id === id);
    this.selectedId.set(id);
    const weeks = competition?.gameweeks ?? [];
    const latest = weeks.length ? weeks[weeks.length - 1] : 1;
    this.gameweek.set(latest);
    this.fromGw.set(weeks[0] ?? 1);
    this.toGw.set(latest);
    this.refreshAll();
  }

  onCompetitionChange(raw: string): void {
    this.selectCompetition(Number(raw));
  }

  onGameweekChange(raw: string): void {
    this.gameweek.set(Number(raw));
    this.loadTeam();
  }

  onCompareChange(): void {
    this.loadCompare();
  }

  hideImage(event: Event): void {
    (event.target as HTMLImageElement).style.visibility = 'hidden';
  }

  signed(value: number | null | undefined): string {
    const n = value ?? 0;
    if (n > 0) {
      return `+${n}`;
    }
    return `${n}`;
  }

  private refreshAll(): void {
    this.loadTeam();
    this.loadCompare();
    this.loadTotals();
  }

  private loadTeam(): void {
    const id = this.selectedId();
    if (id == null) {
      return;
    }
    this.competitionService.getTeam(id, this.gameweek() ?? undefined).subscribe({
      next: (view) => this.teamView.set(view),
      error: () => this.error.set('Could not load squad'),
    });
  }

  private loadCompare(): void {
    const id = this.selectedId();
    if (id == null) {
      return;
    }
    this.competitionService.compare(id, this.fromGw(), this.toGw()).subscribe({
      next: (view) => this.compareView.set(view),
      error: () => this.error.set('Could not load week comparison'),
    });
  }

  private loadTotals(): void {
    const id = this.selectedId();
    if (id == null) {
      return;
    }
    this.competitionService.totals(id).subscribe({
      next: (view) => this.totalsView.set(view),
      error: () => this.error.set('Could not load season totals'),
    });
  }
}
