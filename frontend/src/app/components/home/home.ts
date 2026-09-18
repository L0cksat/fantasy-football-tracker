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
import { HomePage, PlayerOfTheWeek } from '../../models/tracker';
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
  private marqueeTween: gsap.core.Tween | null = null;
  private marqueeDistance = 0;

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

  /** Duplicated list for a seamless horizontal marquee loop. */
  readonly marqueePlayers = computed(() => {
    const players = this.home()?.playersOfTheWeek ?? [];
    if (!players.length) {
      return [];
    }
    return [...players, ...players];
  });

  constructor() {
    this.destroyRef.onDestroy(() => this.killMarquee());

    afterRenderEffect(() => {
      const track = this.marqueeTrack()?.nativeElement;
      const count = this.marqueePlayers().length;
      if (!track || !count) {
        this.killMarquee();
        return;
      }
      this.setupMarquee(track);
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

  hideImage(event: Event): void {
    (event.target as HTMLImageElement).style.visibility = 'hidden';
  }

  shirtLabel(player: PlayerOfTheWeek): string {
    return player.shirtNumber != null ? String(player.shirtNumber) : '—';
  }

  isTopPlayer(player: PlayerOfTheWeek): boolean {
    const top = this.topPlayerOfTheWeek();
    return top != null && top.competitionId === player.competitionId && top.playerId === player.playerId;
  }

  private setupMarquee(track: HTMLElement): void {
    const distance = track.scrollWidth / 2;
    if (distance <= 0) {
      return;
    }

    // Skip rebuild when the track width has not changed (e.g. image layout settle).
    if (this.marqueeTween && this.marqueeDistance === distance) {
      return;
    }

    const wasPaused = this.marqueeTween?.paused() ?? false;
    this.killMarquee();
    this.marqueeDistance = distance;

    const pixelsPerSecond = 28;
    this.marqueeTween = gsap.fromTo(
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
      this.marqueeTween.pause();
    }
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
}
