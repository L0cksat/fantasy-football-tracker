import { DecimalPipe, NgClass, NgStyle, NgTemplateOutlet } from '@angular/common';
import {
  afterRenderEffect,
  Component,
  DestroyRef,
  ElementRef,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import gsap from 'gsap';
import { AllTimeHighestScorer, HomePage, PlayerOfTheWeek } from '../../models/tracker';
import { HomeService } from '../../services/home';

@Component({
  selector: 'app-home',
  imports: [DecimalPipe, NgClass, NgStyle, NgTemplateOutlet, RouterLink],
  templateUrl: './home.html',
  styleUrl: './home.css',
})
export class HomeComponent {
  private readonly homeService = inject(HomeService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly marqueeTrack = viewChild<ElementRef<HTMLElement>>('marqueeTrack');
  private readonly goatMarqueeTrack = viewChild<ElementRef<HTMLElement>>('goatMarqueeTrack');
  private marqueeTween: gsap.core.Tween | null = null;
  private marqueeDistance = 0;
  private goatMarqueeTween: gsap.core.Tween | null = null;
  private goatMarqueeDistance = 0;

  readonly home = signal<HomePage | null>(null);
  readonly error = signal<string | null>(null);
  readonly loading = signal(true);

  readonly colorMix = computed(() => {
    const brands = this.home()?.leagueBrands ?? [];
    const stops: string[] = [];
    brands.forEach((brand, index) => {
      if (!brand.primaryColor || !brand.secondaryColor) {
        return;
      }
      const start = Math.round((index / Math.max(brands.length, 1)) * 100);
      const mid = Math.round(((index + 0.5) / Math.max(brands.length, 1)) * 100);
      stops.push(`${brand.primaryColor} ${start}%`, `${brand.secondaryColor} ${mid}%`);
    });
    if (!stops.length) {
      return 'linear-gradient(135deg, #07140d, #102419)';
    }
    return `linear-gradient(125deg, ${stops.join(', ')})`;
  });

  readonly leaguesHref = computed(() => {
    const page = this.home();
    if (page?.defaultCompetitionId != null) {
      return ['/leagues'];
    }
    return ['/leagues'];
  });

  readonly leaguesQuery = computed(() => {
    const id = this.home()?.defaultCompetitionId;
    return id != null ? { competition: id } : {};
  });

  /** Highest scorer across every competition’s player of the week. */
  readonly topPlayerOfTheWeek = computed(() => {
    const players = this.home()?.playersOfTheWeek ?? [];
    if (!players.length) {
      return null;
    }
    return players.reduce((best, player) => (player.points > best.points ? player : best));
  });

  /** Highest season total across every competition’s all-time leader. */
  readonly topAllTimeScorer = computed(() => {
    const players = this.home()?.allTimeHighestScorers ?? [];
    if (!players.length) {
      return null;
    }
    return players.reduce((best, player) =>
      player.totalPoints > best.totalPoints ? player : best,
    );
  });

  /** Duplicated list for a seamless horizontal marquee loop. */
  readonly marqueePlayers = computed(() => {
    const players = this.home()?.playersOfTheWeek ?? [];
    if (!players.length) {
      return [];
    }
    return [...players, ...players];
  });

  /** Duplicated all-time leaders for the season marquee. */
  readonly marqueeGoats = computed(() => {
    const players = this.home()?.allTimeHighestScorers ?? [];
    if (!players.length) {
      return [];
    }
    return [...players, ...players];
  });

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.killMarquee();
      this.killGoatMarquee();
    });

    afterRenderEffect(() => {
      const track = this.marqueeTrack()?.nativeElement;
      const count = this.marqueePlayers().length;
      if (!track || !count) {
        this.killMarquee();
      } else {
        this.setupMarquee(track);
      }

      const goatTrack = this.goatMarqueeTrack()?.nativeElement;
      const goatCount = this.marqueeGoats().length;
      if (!goatTrack || !goatCount) {
        this.killGoatMarquee();
      } else {
        this.setupGoatMarquee(goatTrack);
      }
    });

    this.homeService.getHome().subscribe({
      next: (page) => {
        this.home.set(page);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Could not reach the backend on http://localhost:8080');
      },
    });
  }

  pauseMarquee(): void {
    this.marqueeTween?.pause();
  }

  resumeMarquee(): void {
    this.marqueeTween?.resume();
  }

  pauseGoatMarquee(): void {
    this.goatMarqueeTween?.pause();
  }

  resumeGoatMarquee(): void {
    this.goatMarqueeTween?.resume();
  }

  hideImage(event: Event): void {
    (event.target as HTMLImageElement).style.visibility = 'hidden';
  }

  shirtLabel(player: Pick<PlayerOfTheWeek, 'shirtNumber'> | Pick<AllTimeHighestScorer, 'shirtNumber'>): string {
    return player.shirtNumber != null ? String(player.shirtNumber) : '—';
  }

  isTopPlayer(player: PlayerOfTheWeek): boolean {
    const top = this.topPlayerOfTheWeek();
    return top != null && top.competitionId === player.competitionId && top.playerId === player.playerId;
  }

  isTopGoat(player: AllTimeHighestScorer): boolean {
    const top = this.topAllTimeScorer();
    return top != null && top.competitionId === player.competitionId && top.playerId === player.playerId;
  }

  private setupMarquee(track: HTMLElement): void {
    const distance = track.scrollWidth / 2;
    if (distance <= 0) {
      return;
    }

    if (this.marqueeTween && this.marqueeDistance === distance) {
      return;
    }

    const wasPaused = this.marqueeTween?.paused() ?? false;
    this.killMarquee();
    this.marqueeDistance = distance;
    this.marqueeTween = this.createMarqueeTween(track, distance, wasPaused);
  }

  private setupGoatMarquee(track: HTMLElement): void {
    const distance = track.scrollWidth / 2;
    if (distance <= 0) {
      return;
    }

    if (this.goatMarqueeTween && this.goatMarqueeDistance === distance) {
      return;
    }

    const wasPaused = this.goatMarqueeTween?.paused() ?? false;
    this.killGoatMarquee();
    this.goatMarqueeDistance = distance;
    this.goatMarqueeTween = this.createMarqueeTween(track, distance, wasPaused);
  }

  private createMarqueeTween(
    track: HTMLElement,
    distance: number,
    wasPaused: boolean,
  ): gsap.core.Tween {
    const pixelsPerSecond = 28;
    const tween = gsap.fromTo(
      track,
      { x: 0 },
      {
        x: -distance,
        duration: distance / pixelsPerSecond,
        ease: 'none',
        repeat: -1,
      },
    );
    if (wasPaused) {
      tween.pause();
    }
    return tween;
  }

  private killMarquee(): void {
    this.marqueeTween?.kill();
    this.marqueeTween = null;
    this.marqueeDistance = 0;
    const track = this.marqueeTrack()?.nativeElement;
    if (track) {
      gsap.set(track, { clearProps: 'transform' });
    }
  }

  private killGoatMarquee(): void {
    this.goatMarqueeTween?.kill();
    this.goatMarqueeTween = null;
    this.goatMarqueeDistance = 0;
    const track = this.goatMarqueeTrack()?.nativeElement;
    if (track) {
      gsap.set(track, { clearProps: 'transform' });
    }
  }
}
