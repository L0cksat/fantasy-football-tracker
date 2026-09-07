export interface Competition {
  id: number;
  source: string;
  externalId: string;
  name: string;
  season: string;
  slug: string;
  teamName: string | null;
  gameweeks: number[];
}

export interface TeamView {
  competition: { id: number; name: string; season: string; slug: string };
  team: { id: number; name: string; managerName: string | null };
  gameweek: {
    number: number;
    name: string;
    status: string;
    startsAt: string | null;
    endsAt: string | null;
  };
  teamPoints: number;
  tripleCaptain: boolean;
  transferPenalty: number;
  picks: PickView[];
  transfers: TransferView[];
}

export interface TransferView {
  direction: 'in' | 'out';
  playerId: number;
  externalId: string;
  name: string;
  playerPortraitUrl: string | null;
  position: string | null;
  club: string | null;
  clubCrestUrl: string | null;
  price: number | null;
}

export interface PickView {
  playerId: number;
  externalId: string;
  name: string;
  playerPortraitUrl: string | null;
  position: string | null;
  club: string | null;
  clubCrestUrl: string | null;
  role: string;
  captain: boolean;
  viceCaptain: boolean;
  captainMultiplier: number;
  basePoints: number;
  points: number;
  rating: number | null;
  breakdown: string | null;
}

export interface CompareView {
  fromGameweek: number;
  toGameweek: number;
  teamFromPoints: number;
  teamToPoints: number;
  teamDelta: number;
  players: PlayerDelta[];
}

export interface PlayerDelta {
  playerId: number;
  name: string;
  playerPortraitUrl: string | null;
  position: string | null;
  club: string | null;
  fromRole: string | null;
  toRole: string | null;
  fromPoints: number;
  toPoints: number;
  delta: number;
}

export interface TotalsView {
  competitionId: number;
  teamName: string;
  totalPoints: number;
  gameweeks: { number: number; name: string; points: number }[];
}
