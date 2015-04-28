package fi.solita.botsofbf.dto;

import java.util.*;
import java.util.stream.Collectors;

public class GameState {

    public final Map map;
    public final Set<Player> players;
    public final Set<Player> finishedPlayers;
    public final Set<Item> items;
    public final int round;
    public final List<ShootingLine> shootingLines;

    public GameState(final Map map) {
        this.map = map;
        this.round = 1;
        this.finishedPlayers = new HashSet<>();
        this.players = new HashSet<>();
        this.items = new HashSet<>();
        this.shootingLines = new ArrayList<>();
    }

    private GameState(final Map map, final int round, final Set<Player> players,
                      Set<Player> finishedPlayers, final Set<Item> items, final List<ShootingLine> shootingLines) {
        this.map = map;
        this.round = round;
        this.players = players;
        this.finishedPlayers = finishedPlayers;
        this.items = items;
        this.shootingLines = shootingLines;
    }

    public GameState addPlayer(final Player player) {
        boolean nameReserved = players.stream().anyMatch(p -> p.name.equals(player.name));
        if ( nameReserved ) {
            throw new IllegalArgumentException("Player already exists.");
        }

        Set<Player> newPlayers = new HashSet<>(players);
        newPlayers.add(player);
        return new GameState(map, round, newPlayers, finishedPlayers, items, shootingLines);
    }

    public GameState addItem(final Item item) {
        Set<Item> newItems = new HashSet<>(items);
        newItems.add(item);
        return new GameState(map, round, players, finishedPlayers, newItems, shootingLines);
    }

    public GameState newRound() {
        List<ShootingLine> newShootingLines = shootingLines.stream()
                .map(line -> line.incAge())
                .filter(line -> line.age < 3)
                .collect(Collectors.toList());
        return new GameState(map, round + 1, players, finishedPlayers, items, newShootingLines);
    }

    public Player getPlayer(UUID playerId) {
        return players.stream().filter(p -> p.id.equals(playerId)).findFirst().get();
    }

    public GameState addInvalidMove(Player player) {
        Player newPlayer = player.decreaseHealth(20);
        return new GameState(map, round, replacePlayer(players, newPlayer), finishedPlayers, items, shootingLines);
    }

    public GameState removeDeadPlayers() {
        Set<Player> alivePlayers = players.stream()
                .filter(p -> p.health > 0)
                .collect(Collectors.toSet());

        return new GameState(map, round, alivePlayers, finishedPlayers, items, shootingLines);
    }


    private Set<Player> getOtherPlayers(Player removedPlayer) {
        return players.stream().filter(p -> !p.id.equals(removedPlayer.id)).collect(Collectors.toSet());
    }

    private boolean playerGotItem(Move move, Player player) {
        return move == Move.PICK && player.lastItem.isPresent() && player.timeInState >= player.lastItem.get().getPickTime();
    }

    private static int manhattanDistance(Player p1, Player p2) {
        return Math.abs(p1.position.x - p2.position.x) + Math.abs(p1.position.y - p2.position.y);
    }

    private static Optional<Player> findClosestPlayer(Player fromPlayer, Set<Player> players) {
        return players.stream()
                .filter(p -> !p.id.equals(fromPlayer.id))
                .sorted((p1, p2) -> manhattanDistance(fromPlayer, p2) - manhattanDistance(fromPlayer, p1))
                .findFirst();
    }

    public GameState movePlayer(UUID playerId, Move move) {
        final Player player = getPlayer(playerId);
        Player newPlayer = null;
        Optional<Player> affectedPlayer = Optional.empty();
        final List<ShootingLine> newShootingLines = new ArrayList(shootingLines);

        if ( move == Move.PICK ) {
            newPlayer = pickItem(player);
        }
        else if ( move == Move.USE ) {
            if ( !player.hasUnusedWeapon() ) {
                throw new IllegalStateException(String.format("%s is trying to use an already used item", player.name));
            }
            Optional<Player> closestPlayer = findClosestPlayer(player, players);
            if ( closestPlayer.isPresent() ) {
                affectedPlayer = Optional.of(closestPlayer.get().decreaseHealth(50));
                newPlayer = player.useFirstUsableItem();
                newShootingLines.add(ShootingLine.of(player.position, closestPlayer.get().position));
            }
        }
        else {
            newPlayer = movePlayer(player, move);
        }


        final Set<Player> newPlayers = affectedPlayer.isPresent() ?
                replacePlayer(replacePlayer(players, newPlayer), affectedPlayer.get()) :
                replacePlayer(players, newPlayer);

        final Set<Item> newItems = playerGotItem(move, player) ? removeItem(player.position) : items;

        if ( map.exit.equals(newPlayer.position) ) {
            finishedPlayers.add(newPlayer);
            return new GameState(map, round, getOtherPlayers(newPlayer), finishedPlayers, newItems, newShootingLines);
        }
        else {
            return new GameState(map, round, newPlayers, finishedPlayers, newItems, newShootingLines);
        }
    }

    public Set<Item> removeItem(Position position) {
        return items.stream().filter(i -> !i.position.equals(position)).collect(Collectors.toSet());
    }

    private Player movePlayer(Player player, Move move) {
        if ( map.isValidPosition(player.position.move(move, map.width, map.height)) ) {
            return player.move(player.position.move(move, map.width, map.height));
        }
        else {
            throw new IllegalStateException(String.format("Invalid move from", player.name));
        }
    }

    private Player pickItem(Player player) {
        final Optional<Item> item = items.stream().filter(i -> i.position.equals(player.position)).findFirst();

        return player.pickItem(item.orElseThrow(() -> new IllegalStateException(
                String.format("%s is trying to pick from invalid location", player.name))));
    }

    private Set<Player> replacePlayer(Set<Player> players, Player newPlayer) {
        final Set<Player> otherPlayers = players.stream()
                .filter(p -> !p.id.equals(newPlayer.id)).collect(Collectors.toSet());
        otherPlayers.add(newPlayer);
        return otherPlayers;
    }

    public GameState spawnItems() {
        if (items.size() < map.maxItemCount && Math.random() > 0.9) {
            int price = randomBetween(100, Player.INITIAL_MONEY_LEFT);
            int discountPercent = randomBetween(10, 90);
            Position pos = map.randomValidPosition(items.stream().map(i -> i.position));
            Item newItem = discountPercent > 70 ?
                    Item.createWeapon(price, discountPercent, pos) :
                    Item.create(price, discountPercent, pos);
            return addItem(newItem);
        } else {
            return this;
        }
    }

    private static int randomBetween(int min, int max) {
        return new Random().nextInt(max - min + 1) + min;
    }

}