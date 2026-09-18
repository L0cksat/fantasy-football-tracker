import { DecimalPipe, NgClass, NgStyle } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CompareView, Competition, PickView, TeamView, TotalsView, TransferHighlight } from '../../models/tracker';
import { CompetitionService } from '../../services/competition';

@Component({
  selector: 'app-dashboard',
  imports: [DecimalPipe, FormsModule, NgClass, NgStyle, RouterLink],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class DashboardComponent {
  private readonly competitionService = inject(CompetitionService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

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

  readonly starters = computed<PickView[]>(() =>
    (this.teamView()?.picks ?? []).filter((pick) => pick.role === 'starter'),
  );
  readonly bench = computed<PickView[]>(() =>
    (this.teamView()?.picks ?? []).filter((pick) => pick.role !== 'starter'),
  );
  readonly isOfficialLaLiga = computed(
    () => this.selectedCompetition()?.source === 'laliga-fantasy',
  );
  readonly isOfficialFpl = computed(
    () => this.selectedCompetition()?.source === 'fpl',
  );
  readonly reserveHeading = computed(() => (this.isOfficialLaLiga() ? 'Squad' : 'Bench'));
  readonly showTransferCounterpart = computed(
    () =>
      this.isOfficialLaLiga() ||
      (this.teamView()?.transfers ?? []).some((move) => !!move.counterpart),
  );

  /** Top point scorer in the selected competition gameweek (your squad). */
  readonly playerOfTheWeek = computed(() => {
    const picks = this.teamView()?.picks ?? [];
    if (!picks.length) {
      return null;
    }
    return picks.reduce((best, pick) => (pick.points > best.points ? pick : best));
  });

  /** Best and worst team gameweeks across the season (from totals). */
  readonly highestScoringGameweek = computed(() => {
    const weeks = this.totalsView()?.gameweeks ?? [];
    if (!weeks.length) {
      return null;
    }
    return weeks.reduce((best, week) => (week.points > best.points ? week : best));
  });

  readonly lowestScoringGameweek = computed(() => {
    const weeks = this.totalsView()?.gameweeks ?? [];
    if (!weeks.length) {
      return null;
    }
    return weeks.reduce((worst, week) => (week.points < worst.points ? week : worst));
  });

  readonly mostExpensivePurchase = computed(() => {
    if (!this.isOfficialLaLiga()) {
      return null;
    }
    return this.teamView()?.transferMarket?.mostExpensivePurchase ?? null;
  });

  readonly highestPlayerSale = computed(() => {
    if (!this.isOfficialLaLiga()) {
      return null;
    }
    return this.teamView()?.transferMarket?.highestSale ?? null;
  });

  transferHighlightShirt(player: TransferHighlight): string {
    return player.shirtNumber != null ? String(player.shirtNumber) : '—';
  }

  transferHighlightMeta(player: TransferHighlight): string {
    const week = player.gameweekName || (player.gameweekNumber != null ? `GW${player.gameweekNumber}` : null);
    const deal = this.counterpartLabel(player);
    if (week && deal) {
      return `${week} · ${deal}`;
    }
    return week || deal || '—';
  }

  transferLabel(direction: string): string {
    if (this.isOfficialLaLiga()) {
      return direction === 'in' ? 'Bought' : 'Sold';
    }
    return direction === 'in' ? 'In' : 'Out';
  }

  priceFormat(): string {
    return this.isOfficialLaLiga() ? '1.1-2' : '1.1-1';
  }

  counterpartLabel(move: { counterpart: string | null; channel: string | null }): string {
    if (!this.isOfficialLaLiga()) {
      return move.counterpart || '—';
    }
    if (move.channel === 'release-clause' && move.counterpart) {
      return `Release clause paid · ${move.counterpart}`;
    }
    return move.counterpart || 'Market';
  }

  hasMarketDeals(scope: {
    soldToMarket: { count: number };
    soldReleaseClause: { count: number };
    boughtFromMarket: { count: number };
    boughtReleaseClause: { count: number };
  } | null | undefined): boolean {
    if (!scope) {
      return false;
    }
    return (
      scope.soldToMarket.count +
        scope.soldReleaseClause.count +
        scope.boughtFromMarket.count +
        scope.boughtReleaseClause.count >
      0
    );
  }

  constructor() {
    this.reloadCompetitions();
    if (typeof window !== 'undefined') {
      window.addEventListener('focus', () => this.refreshCompetitionList());
    }
  }

  /** Refresh gameweek lists after an ingest without resetting the open week. */
  private refreshCompetitionList(): void {
    const current = this.selectedId();
    this.competitionService.getCompetitions().subscribe({
      next: (competitions) => {
        this.competitions.set(competitions);
        if (current == null) {
          return;
        }
        const selected = competitions.find((item) => item.id === current);
        const weeks = selected?.gameweeks ?? [];
        const open = this.gameweek();
        if (open != null && weeks.includes(open)) {
          return;
        }
        if (weeks.length) {
          this.selectCompetition(current, false);
        }
      },
    });
  }

  private reloadCompetitions(): void {
    this.competitionService.getCompetitions().subscribe({
      next: (competitions) => {
        this.competitions.set(competitions);
        this.loading.set(false);
        if (!competitions.length) {
          return;
        }
        const requested = Number(this.route.snapshot.queryParamMap.get('competition'));
        const byQuery = Number.isFinite(requested)
          ? competitions.find((item) => item.id === requested)
          : null;
        const bySlug = competitions.find((item) => item.slug === 'premier-league');
        const initial = byQuery ?? bySlug ?? competitions[0];
        this.selectCompetition(initial.id, false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Could not reach the backend on http://localhost:8080');
      },
    });
  }

  selectCompetition(id: number, syncRoute = true): void {
    const competition = this.competitions().find((item) => item.id === id);
    this.selectedId.set(id);
    if (syncRoute) {
      void this.router.navigate([], {
        relativeTo: this.route,
        queryParams: { competition: id },
        queryParamsHandling: 'merge',
        replaceUrl: true,
      });
    }
    const weeks = competition?.gameweeks ?? [];
    const latest = weeks.length ? weeks[weeks.length - 1] : 1;
    this.gameweek.set(latest);
    this.fromGw.set(weeks[0] ?? 1);
    this.toGw.set(latest);
    // Prefer the latest week that already has a score (skip empty upcoming shells
    // created only by transfers, e.g. Official LaLiga GW7).
    this.competitionService.totals(id).subscribe({
      next: (totals: TotalsView) => {
        if (this.selectedId() !== id) {
          return;
        }
        const scored = totals.gameweeks.map((week: { number: number }) => week.number);
        if (scored.length) {
          const latestScored = scored[scored.length - 1];
          this.gameweek.set(latestScored);
          this.toGw.set(latestScored);
        }
        this.totalsView.set(totals);
        this.loadTeam();
        this.loadCompare();
      },
      error: () => this.refreshAll(),
    });
  }

  onCompetitionChange(raw: string | number): void {
    const id = this.parseSelectNumber(raw);
    if (id == null) {
      return;
    }
    this.selectCompetition(id, true);
  }

  onGameweekChange(raw: string | number): void {
    const week = this.parseSelectNumber(raw);
    if (week == null) {
      return;
    }
    this.gameweek.set(week);
    this.loadTeam();
  }

  onFromChange(raw: string | number): void {
    const week = this.parseSelectNumber(raw);
    if (week == null) {
      return;
    }
    this.fromGw.set(week);
    this.loadCompare();
  }

  onToChange(raw: string | number): void {
    const week = this.parseSelectNumber(raw);
    if (week == null) {
      return;
    }
    this.toGw.set(week);
    this.loadCompare();
  }

  private parseSelectNumber(raw: string | number): number | null {
    if (typeof raw === 'number' && Number.isFinite(raw)) {
      return raw;
    }
    const token = String(raw).split(':').pop()?.trim() ?? '';
    const value = Number(token);
    return Number.isFinite(value) ? value : null;
  }

  isInjured(pick: PickView): boolean {
    return pick.injured === true;
  }

  isSuspended(pick: PickView): boolean {
    return pick.suspended === true;
  }

  hideImage(event: Event): void {
    (event.target as HTMLImageElement).style.visibility = 'hidden';
  }

  shirtLabel(pick: PickView): string {
    return pick.shirtNumber != null ? String(pick.shirtNumber) : '—';
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
