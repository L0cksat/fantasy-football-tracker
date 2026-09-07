-- Remove dummy seed players (external_id ss-*) left over after a real SofaScore import.
USE fantasy_tracker;

DELETE sp FROM squad_pick sp
JOIN player p ON p.id = sp.player_id
WHERE p.external_id LIKE 'ss-%';

DELETE pgs FROM player_gameweek_score pgs
JOIN player p ON p.id = pgs.player_id
WHERE p.external_id LIKE 'ss-%';

DELETE FROM player
WHERE external_id LIKE 'ss-%';
