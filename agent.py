"""The submission entrypoint. The platform imports this file and calls get_move."""

import random

import chess

# Import time runs once per game, inside a 60 second budget, before your clock starts.
# Load weights and build tables out here, not inside get_move.


from __future__ import annotations

import json
import random
import time
from pathlib import Path

import chess
import chess.polyglot


INF = 1_000_000
MATE = 100_000
MAX_PLY = 96
EXACT, LOWER, UPPER = 0, 1, 2
TT_LIMIT = 300_000

PIECE_VALUE = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 335,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20_000,
}

# Explicit, independently tunable middle-game and endgame piece-square tables.
# Squares run a1..h8. Black uses the vertically mirrored square.
MG_PST = {
    chess.PAWN: (
        0, 0, 0, 0, 0, 0, 0, 0,
        5, 10, 10, -18, -18, 10, 10, 5,
        4, 2, -6, 4, 4, -6, 2, 4,
        2, 4, 8, 22, 22, 8, 4, 2,
        6, 8, 14, 28, 28, 14, 8, 6,
        12, 16, 24, 34, 34, 24, 16, 12,
        45, 48, 52, 58, 58, 52, 48, 45,
        0, 0, 0, 0, 0, 0, 0, 0,
    ),
    chess.KNIGHT: (
        -55, -38, -28, -24, -24, -28, -38, -55,
        -38, -18, -4, 2, 2, -4, -18, -38,
        -26, -4, 12, 18, 18, 12, -4, -26,
        -20, 4, 18, 26, 26, 18, 4, -20,
        -20, 2, 18, 28, 28, 18, 2, -20,
        -26, -4, 10, 18, 18, 10, -4, -26,
        -38, -18, -4, 2, 2, -4, -18, -38,
        -55, -42, -30, -24, -24, -30, -42, -55,
    ),
    chess.BISHOP: (
        -22, -12, -10, -8, -8, -10, -12, -22,
        -10, 4, 2, 4, 4, 2, 4, -10,
        -8, 6, 10, 14, 14, 10, 6, -8,
        -6, 4, 12, 18, 18, 12, 4, -6,
        -6, 6, 12, 18, 18, 12, 6, -6,
        -8, 8, 12, 12, 12, 12, 8, -8,
        -10, 6, 4, 4, 4, 4, 6, -10,
        -22, -12, -10, -8, -8, -10, -12, -22,
    ),
    chess.ROOK: (
        0, 0, 4, 8, 8, 4, 0, 0,
        -4, 0, 2, 4, 4, 2, 0, -4,
        -6, -2, 0, 2, 2, 0, -2, -6,
        -6, -2, 0, 2, 2, 0, -2, -6,
        -4, 0, 2, 4, 4, 2, 0, -4,
        0, 4, 6, 8, 8, 6, 4, 0,
        16, 20, 22, 24, 24, 22, 20, 16,
        4, 8, 12, 14, 14, 12, 8, 4,
    ),
    chess.QUEEN: (
        -18, -10, -8, -4, -4, -8, -10, -18,
        -10, 0, 2, 2, 2, 2, 0, -10,
        -8, 2, 6, 6, 6, 6, 2, -8,
        -4, 2, 6, 8, 8, 6, 2, -4,
        -2, 4, 6, 8, 8, 6, 4, -2,
        -8, 4, 6, 6, 6, 6, 4, -8,
        -10, 0, 4, 2, 2, 4, 0, -10,
        -18, -10, -8, -4, -4, -8, -10, -18,
    ),
    chess.KING: (
        24, 34, 12, -18, -18, 2, 34, 24,
        18, 18, -2, -20, -20, -8, 18, 18,
        -8, -14, -20, -28, -28, -20, -14, -8,
        -20, -26, -30, -38, -38, -30, -26, -20,
        -30, -36, -42, -48, -48, -42, -36, -30,
        -38, -44, -50, -56, -56, -50, -44, -38,
        -46, -52, -58, -64, -64, -58, -52, -46,
        -54, -60, -66, -72, -72, -66, -60, -54,
    ),
}

EG_PST = {
    chess.PAWN: (
        0, 0, 0, 0, 0, 0, 0, 0,
        8, 10, 12, 14, 14, 12, 10, 8,
        12, 14, 18, 22, 22, 18, 14, 12,
        18, 22, 28, 34, 34, 28, 22, 18,
        28, 34, 42, 50, 50, 42, 34, 28,
        44, 52, 62, 72, 72, 62, 52, 44,
        70, 78, 88, 98, 98, 88, 78, 70,
        0, 0, 0, 0, 0, 0, 0, 0,
    ),
    chess.KNIGHT: (
        -45, -30, -20, -16, -16, -20, -30, -45,
        -30, -12, -2, 4, 4, -2, -12, -30,
        -20, -2, 10, 16, 16, 10, -2, -20,
        -16, 4, 16, 22, 22, 16, 4, -16,
        -16, 4, 16, 22, 22, 16, 4, -16,
        -20, -2, 10, 16, 16, 10, -2, -20,
        -30, -12, -2, 4, 4, -2, -12, -30,
        -45, -30, -20, -16, -16, -20, -30, -45,
    ),
    chess.BISHOP: (
        -18, -10, -8, -6, -6, -8, -10, -18,
        -10, 2, 4, 6, 6, 4, 2, -10,
        -8, 4, 8, 12, 12, 8, 4, -8,
        -6, 6, 12, 16, 16, 12, 6, -6,
        -6, 6, 12, 16, 16, 12, 6, -6,
        -8, 4, 8, 12, 12, 8, 4, -8,
        -10, 2, 4, 6, 6, 4, 2, -10,
        -18, -10, -8, -6, -6, -8, -10, -18,
    ),
    chess.ROOK: (
        -2, 0, 4, 6, 6, 4, 0, -2,
        2, 4, 6, 8, 8, 6, 4, 2,
        2, 4, 6, 8, 8, 6, 4, 2,
        2, 4, 6, 8, 8, 6, 4, 2,
        2, 4, 6, 8, 8, 6, 4, 2,
        4, 6, 8, 10, 10, 8, 6, 4,
        10, 12, 14, 16, 16, 14, 12, 10,
        2, 4, 8, 10, 10, 8, 4, 2,
    ),
    chess.QUEEN: (
        -16, -10, -6, -4, -4, -6, -10, -16,
        -10, -2, 2, 4, 4, 2, -2, -10,
        -6, 2, 6, 8, 8, 6, 2, -6,
        -4, 4, 8, 12, 12, 8, 4, -4,
        -4, 4, 8, 12, 12, 8, 4, -4,
        -6, 2, 6, 8, 8, 6, 2, -6,
        -10, -2, 2, 4, 4, 2, -2, -10,
        -16, -10, -6, -4, -4, -6, -10, -16,
    ),
    chess.KING: (
        -50, -30, -20, -10, -10, -20, -30, -50,
        -30, -12, 0, 8, 8, 0, -12, -30,
        -20, 0, 14, 22, 22, 14, 0, -20,
        -10, 8, 22, 32, 32, 22, 8, -10,
        -10, 8, 22, 32, 32, 22, 8, -10,
        -20, 0, 14, 22, 22, 14, 0, -20,
        -30, -12, 0, 8, 8, 0, -12, -30,
        -50, -30, -20, -10, -10, -20, -30, -50,
    ),
}

DEFAULT_WEIGHTS = {
    "pawn": 100.0,
    "knight": 320.0,
    "bishop": 335.0,
    "rook": 500.0,
    "queen": 900.0,
    "pst_mg": 1.0,
    "pst_eg": 1.0,
    "bishop_pair": 28.0,
    "mobility": 3.2,
    "doubled_pawn": -14.0,
    "isolated_pawn": -11.0,
    "backward_pawn": -10.0,
    "passed_pawn": 3.4,
    "connected_passer": 4.5,
    "protected_passer": 5.5,
    "rook_open_file": 18.0,
    "rook_semi_open_file": 10.0,
    "rook_seventh": 18.0,
    "knight_outpost": 20.0,
    "king_shield": 11.0,
    "king_open_file": -17.0,
    "castled_king": 26.0,
    "undeveloped_minor": -8.0,
    "early_queen": -14.0,
    "trapped_piece": -14.0,
    "space": 2.0,
    "tempo": 9.0,
}
FEATURE_NAMES = tuple(DEFAULT_WEIGHTS)


def _load_weights() -> tuple[dict[str, float], bool]:
    path = Path(__file__).with_name("weights") / "linear_eval.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        supplied = payload.get("weights", payload)
        weights = DEFAULT_WEIGHTS.copy()
        for name in FEATURE_NAMES:
            if name in supplied:
                weights[name] = float(supplied[name])
        return weights, bool(payload.get("training", {}).get("games", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        return DEFAULT_WEIGHTS.copy(), False


EVAL_WEIGHTS, LEARNED_MODEL_ACTIVE = _load_weights()

# Entries: depth, score, bound flag, best move, generation.
TT: dict[int, tuple[int, int, int, chess.Move | None, int]] = {}
HISTORY: dict[tuple[bool, int, int], int] = {}
KILLERS: list[list[chess.Move | None]] = [[None, None] for _ in range(MAX_PLY)]
POSITION_COUNTS: dict[int, int] = {}
EVAL_CACHE: dict[int, int] = {}
TT_GENERATION = 0

_deadline = 0.0
_nodes = 0
_completed_depth = 0


class SearchTimeout(Exception):
    pass


def _key(board: chess.Board) -> int:
    return chess.polyglot.zobrist_hash(board)


def _check_time() -> None:
    global _nodes
    _nodes += 1
    if (_nodes & 63) == 0 and time.perf_counter() >= _deadline:
        raise SearchTimeout


def _terminal_draw(board: chess.Board) -> bool:
    return board.halfmove_clock >= 100 or board.is_insufficient_material()


def _relative_rank(square: int, colour: bool) -> int:
    rank = chess.square_rank(square)
    return rank if colour == chess.WHITE else 7 - rank


def extract_features(board: chess.Board) -> dict[str, float]:
    """Return interpretable features from White's perspective."""
    features = {name: 0.0 for name in FEATURE_NAMES}

    phase = 0
    phase_value = {chess.KNIGHT: 1, chess.BISHOP: 1, chess.ROOK: 2, chess.QUEEN: 4}
    for piece, value in phase_value.items():
        phase += value * (
            len(board.pieces(piece, chess.WHITE)) + len(board.pieces(piece, chess.BLACK))
        )
    phase = min(24, phase)

    for colour, sign in ((chess.WHITE, 1.0), (chess.BLACK, -1.0)):
        own_pawns = board.pieces(chess.PAWN, colour)
        enemy_pawns = board.pieces(chess.PAWN, not colour)
        own_occupied = board.occupied_co[colour]
        file_counts = [0] * 8
        enemy_file_counts = [0] * 8
        space = chess.BB_EMPTY
        for square in own_pawns:
            file_counts[chess.square_file(square)] += 1
        for square in enemy_pawns:
            enemy_file_counts[chess.square_file(square)] += 1

        for piece, name in (
            (chess.PAWN, "pawn"),
            (chess.KNIGHT, "knight"),
            (chess.BISHOP, "bishop"),
            (chess.ROOK, "rook"),
            (chess.QUEEN, "queen"),
        ):
            pieces = board.pieces(piece, colour)
            features[name] += sign * len(pieces)
            for square in pieces:
                attacks = board.attacks(square)
                space |= int(attacks)
                relative = square if colour == chess.WHITE else chess.square_mirror(square)
                features["pst_mg"] += sign * MG_PST[piece][relative] * phase / 24.0
                features["pst_eg"] += sign * EG_PST[piece][relative] * (24 - phase) / 24.0
                if piece != chess.PAWN:
                    mobility = len(attacks & ~own_occupied)
                    features["mobility"] += sign * mobility
                    if piece in (chess.KNIGHT, chess.BISHOP, chess.ROOK) and mobility <= 1:
                        features["trapped_piece"] += sign

        king_square = board.king(colour)
        if king_square is not None:
            relative = king_square if colour == chess.WHITE else chess.square_mirror(king_square)
            features["pst_mg"] += sign * MG_PST[chess.KING][relative] * phase / 24.0
            features["pst_eg"] += sign * EG_PST[chess.KING][relative] * (24 - phase) / 24.0
            king_file = chess.square_file(king_square)
            king_rank = chess.square_rank(king_square)
            home_rank = 0 if colour == chess.WHITE else 7
            direction = 1 if colour == chess.WHITE else -1
            if king_rank == home_rank and king_file in (2, 6):
                features["castled_king"] += sign
            if file_counts[king_file] == 0:
                features["king_open_file"] += sign
            shield_rank = king_rank + direction
            if 0 <= shield_rank <= 7:
                for file in range(max(0, king_file - 1), min(7, king_file + 1) + 1):
                    if chess.square(file, shield_rank) in own_pawns:
                        features["king_shield"] += sign

        if len(board.pieces(chess.BISHOP, colour)) >= 2:
            features["bishop_pair"] += sign
        features["doubled_pawn"] += sign * sum(max(0, count - 1) for count in file_counts)

        for square in own_pawns:
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            advance = _relative_rank(square, colour)
            if (file == 0 or file_counts[file - 1] == 0) and (
                file == 7 or file_counts[file + 1] == 0
            ):
                features["isolated_pawn"] += sign
            else:
                direction = 8 if colour == chess.WHITE else -8
                forward = square + direction
                has_rear_support = any(
                    abs(chess.square_file(other) - file) == 1
                    and _relative_rank(other, colour) <= advance
                    for other in own_pawns
                )
                if (
                    not has_rear_support
                    and 0 <= forward < 64
                    and bool(board.attackers(not colour, forward) & enemy_pawns)
                ):
                    features["backward_pawn"] += sign

            passed = True
            for enemy in enemy_pawns:
                enemy_file = chess.square_file(enemy)
                enemy_rank = chess.square_rank(enemy)
                if abs(enemy_file - file) <= 1 and (
                    (colour == chess.WHITE and enemy_rank > rank)
                    or (colour == chess.BLACK and enemy_rank < rank)
                ):
                    passed = False
                    break
            if passed:
                features["passed_pawn"] += sign * max(1, advance * advance)
                connected = any(
                    abs(chess.square_file(other) - file) == 1
                    and abs(chess.square_rank(other) - rank) <= 1
                    for other in own_pawns
                )
                if connected:
                    features["connected_passer"] += sign * max(1, advance)
                if board.attackers(colour, square) & own_pawns:
                    features["protected_passer"] += sign * max(1, advance)

        for square in board.pieces(chess.ROOK, colour):
            file = chess.square_file(square)
            if file_counts[file] == 0 and enemy_file_counts[file] == 0:
                features["rook_open_file"] += sign
            elif file_counts[file] == 0:
                features["rook_semi_open_file"] += sign
            if _relative_rank(square, colour) == 6:
                features["rook_seventh"] += sign

        for square in board.pieces(chess.KNIGHT, colour):
            file = chess.square_file(square)
            advance = _relative_rank(square, colour)
            if advance >= 3 and board.attackers(colour, square) & own_pawns:
                challengeable = False
                for enemy in enemy_pawns:
                    if abs(chess.square_file(enemy) - file) != 1:
                        continue
                    enemy_advance = _relative_rank(enemy, not colour)
                    if enemy_advance <= 4:
                        challengeable = True
                        break
                if not challengeable:
                    features["knight_outpost"] += sign

        starting_minors = (
            (chess.B1, chess.G1, chess.C1, chess.F1)
            if colour == chess.WHITE
            else (chess.B8, chess.G8, chess.C8, chess.F8)
        )
        for square in starting_minors:
            piece = board.piece_at(square)
            if piece and piece.color == colour and piece.piece_type in (chess.KNIGHT, chess.BISHOP):
                features["undeveloped_minor"] += sign

        if board.fullmove_number <= 10:
            queen_home = chess.D1 if colour == chess.WHITE else chess.D8
            queens = board.pieces(chess.QUEEN, colour)
            if queens and queen_home not in queens:
                features["early_queen"] += sign

        enemy_half = (
            chess.BB_RANK_5 | chess.BB_RANK_6 | chess.BB_RANK_7 | chess.BB_RANK_8
            if colour == chess.WHITE
            else chess.BB_RANK_1 | chess.BB_RANK_2 | chess.BB_RANK_3 | chess.BB_RANK_4
        )
        features["space"] += sign * chess.popcount(space & enemy_half & ~own_occupied)

    features["tempo"] = 1.0 if board.turn == chess.WHITE else -1.0
    return features


def _evaluate_white(board: chess.Board) -> int:
    key = _key(board)
    cached = EVAL_CACHE.get(key)
    if cached is not None:
        return cached
    features = extract_features(board)
    score = int(sum(EVAL_WEIGHTS[name] * features[name] for name in FEATURE_NAMES))
    EVAL_CACHE[key] = score
    return score


def _evaluate(board: chess.Board) -> int:
    score = _evaluate_white(board)
    return score if board.turn == chess.WHITE else -score


def _captured_piece(board: chess.Board, move: chess.Move) -> int:
    if board.is_en_passant(move):
        return chess.PAWN
    return board.piece_type_at(move.to_square) or 0


def _see(board: chess.Board, move: chess.Move) -> int:
    """Fast static exchange estimate for capture ordering and pruning."""
    victim = _captured_piece(board, move)
    attacker = board.piece_type_at(move.from_square) or chess.PAWN
    promotion_gain = PIECE_VALUE.get(move.promotion or 0, 0) - (100 if move.promotion else 0)
    immediate = PIECE_VALUE.get(victim, 0) + promotion_gain
    target = move.to_square
    moving_colour = board.turn
    board.push(move)
    can_recapture = board.is_attacked_by(board.turn, target)
    is_defended = board.is_attacked_by(moving_colour, target)
    board.pop()
    if not can_recapture:
        return immediate
    loss = PIECE_VALUE.get(move.promotion or attacker, PIECE_VALUE[attacker])
    # A defended capture often permits a recapture back; retain half of the
    # moving piece's value as a conservative approximation of that continuation.
    if is_defended:
        loss //= 2
    return immediate - loss


def _capture_value(board: chess.Board, move: chess.Move) -> int:
    attacker = board.piece_type_at(move.from_square) or chess.PAWN
    victim = _captured_piece(board, move)
    return 10 * PIECE_VALUE.get(victim, 0) - PIECE_VALUE[attacker]


def _move_score(board: chess.Board, move: chess.Move, tt_move: chess.Move | None, ply: int) -> int:
    if move == tt_move:
        return 10_000_000
    if move.promotion:
        return 8_000_000 + PIECE_VALUE[move.promotion]
    if board.is_capture(move):
        return 6_000_000 + _see(board, move) * 32 + _capture_value(board, move)
    if ply < MAX_PLY:
        if move == KILLERS[ply][0]:
            return 4_000_000
        if move == KILLERS[ply][1]:
            return 3_900_000
    return HISTORY.get((board.turn, move.from_square, move.to_square), 0)


def _ordered_moves(
    board: chess.Board, tt_move: chess.Move | None, ply: int, tactical_only: bool = False
) -> list[chess.Move]:
    if tactical_only:
        moves = [
            move
            for move in board.legal_moves
            if board.is_capture(move) or move.promotion is not None
        ]
    else:
        moves = list(board.legal_moves)
    moves.sort(key=lambda move: _move_score(board, move, tt_move, ply), reverse=True)
    return moves


def _score_to_tt(score: int, ply: int) -> int:
    if score > MATE - MAX_PLY:
        return score + ply
    if score < -MATE + MAX_PLY:
        return score - ply
    return score


def _score_from_tt(score: int, ply: int) -> int:
    if score > MATE - MAX_PLY:
        return score - ply
    if score < -MATE + MAX_PLY:
        return score + ply
    return score


def _is_repetition(board: chess.Board, ply: int) -> bool:
    key = _key(board)
    if POSITION_COUNTS.get(key, 0) >= 2:
        return True
    return ply >= 4 and board.is_repetition(3)


def _quiescence(board: chess.Board, alpha: int, beta: int, ply: int) -> int:
    _check_time()
    if ply >= MAX_PLY:
        return _evaluate(board)
    if _terminal_draw(board) or _is_repetition(board, ply):
        return 0

    in_check = board.is_check()
    stand_pat = -INF if in_check else _evaluate(board)
    if not in_check:
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)

    moves = _ordered_moves(board, None, ply, tactical_only=not in_check)
    if not moves:
        if in_check:
            return -MATE + ply
        return 0 if not any(board.legal_moves) else alpha

    for move in moves:
        if not in_check and move.promotion is None:
            if _see(board, move) < 0 and not board.gives_check(move):
                continue
            victim = _captured_piece(board, move)
            if stand_pat + PIECE_VALUE.get(victim, 0) + 160 < alpha:
                continue
        board.push(move)
        score = -_quiescence(board, -beta, -alpha, ply + 1)
        board.pop()
        if score >= beta:
            return beta
        alpha = max(alpha, score)
    return alpha


def _negamax(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
    extension_budget: int,
) -> int:
    _check_time()
    if ply >= MAX_PLY:
        return _evaluate(board)
    if _terminal_draw(board) or _is_repetition(board, ply):
        return 0

    in_check = board.is_check()
    if in_check and depth > 0 and extension_budget > 0:
        depth += 1
        extension_budget -= 1
    if depth <= 0:
        return _quiescence(board, alpha, beta, ply)

    original_alpha, original_beta = alpha, beta
    key = _key(board)
    entry = TT.get(key)
    tt_move = entry[3] if entry else None
    if entry and entry[0] >= depth:
        tt_score = _score_from_tt(entry[1], ply)
        if entry[2] == EXACT:
            return tt_score
        if entry[2] == LOWER:
            alpha = max(alpha, tt_score)
        else:
            beta = min(beta, tt_score)
        if alpha >= beta:
            return tt_score

    # Full learned feature extraction is valuable at leaves but too expensive
    # to repeat at every deep internal node. Depth-one nodes need it for
    # futility pruning; deeper nodes rely on the search and transposition table.
    static_eval = _evaluate(board) if depth == 1 else 0
    has_non_pawn = any(
        board.pieces(piece, board.turn)
        for piece in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
    )
    if depth >= 3 and not in_check and has_non_pawn and beta < MATE - MAX_PLY:
        board.push(chess.Move.null())
        score = -_negamax(board, depth - 3, -beta, -beta + 1, ply + 1, extension_budget)
        board.pop()
        if score >= beta:
            return beta

    moves = _ordered_moves(board, tt_move, ply)
    if not moves:
        return -MATE + ply if in_check else 0

    best_score = -INF
    best_move = None
    for index, move in enumerate(moves):
        quiet = not board.is_capture(move) and move.promotion is None
        if (
            depth == 1
            and index > 0
            and quiet
            and not in_check
            and static_eval + 120 <= alpha
            and not board.gives_check(move)
        ):
            continue

        board.push(move)
        if index == 0:
            score = -_negamax(
                board, depth - 1, -beta, -alpha, ply + 1, extension_budget
            )
        else:
            reduction = 1 if depth >= 3 and index >= 4 and quiet and not in_check else 0
            score = -_negamax(
                board,
                depth - 1 - reduction,
                -alpha - 1,
                -alpha,
                ply + 1,
                extension_budget,
            )
            if score > alpha and reduction:
                score = -_negamax(
                    board, depth - 1, -alpha - 1, -alpha, ply + 1, extension_budget
                )
            if score > alpha and score < beta:
                score = -_negamax(
                    board, depth - 1, -beta, -alpha, ply + 1, extension_budget
                )
        board.pop()

        if score > best_score:
            best_score, best_move = score, move
        alpha = max(alpha, score)
        if alpha >= beta:
            if quiet:
                if ply < MAX_PLY and move != KILLERS[ply][0]:
                    KILLERS[ply][1] = KILLERS[ply][0]
                    KILLERS[ply][0] = move
                history_key = (board.turn, move.from_square, move.to_square)
                HISTORY[history_key] = min(
                    1_000_000, HISTORY.get(history_key, 0) + depth * depth
                )
            break

    if best_move is None:
        best_score, best_move = _evaluate(board), moves[0]
    flag = UPPER if best_score <= original_alpha else LOWER if best_score >= original_beta else EXACT
    old = TT.get(key)
    if old is None or depth >= old[0] or old[4] != TT_GENERATION:
        TT[key] = (depth, _score_to_tt(best_score, ply), flag, best_move, TT_GENERATION)
    return best_score


def _root_search(
    board: chess.Board,
    depth: int,
    preferred: chess.Move,
    alpha: int = -INF,
    beta: int = INF,
) -> tuple[int, chess.Move]:
    original_alpha, original_beta = alpha, beta
    best_score = -INF
    best_move = preferred
    entry = TT.get(_key(board))
    tt_move = entry[3] if entry and entry[3] in board.legal_moves else preferred

    for index, move in enumerate(_ordered_moves(board, tt_move, 0)):
        board.push(move)
        if index == 0:
            score = -_negamax(board, depth - 1, -beta, -alpha, 1, 1)
        else:
            score = -_negamax(board, depth - 1, -alpha - 1, -alpha, 1, 1)
            if score > alpha and score < beta:
                score = -_negamax(board, depth - 1, -beta, -alpha, 1, 1)
        board.pop()
        if score > best_score:
            best_score, best_move = score, move
        alpha = max(alpha, score)
        if alpha >= beta:
            break

    flag = UPPER if best_score <= original_alpha else LOWER if best_score >= original_beta else EXACT
    TT[_key(board)] = (
        depth,
        _score_to_tt(best_score, 0),
        flag,
        best_move,
        TT_GENERATION,
    )
    return best_score, best_move


def _build_opening_book() -> dict[int, tuple[chess.Move, ...]]:
    lines = (
        "e2e4 e7e5 g1f3 b8c6 f1c4 g8f6 d2d3 f8c5 e1g1 d7d6 c2c3 e8g8",
        "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1 f8e7 f1e1 b7b5 a4b3 d7d6 c2c3 e8g8",
        "e2e4 e7e5 g1f3 b8c6 d2d4 e5d4 f3d4 g8f6 b1c3 f8b4",
        "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6",
        "e2e4 c7c6 d2d4 d7d5 b1c3 d5e4 c3e4 c8f5",
        "e2e4 e7e6 d2d4 d7d5 b1c3 g8f6 e4e5 f6d7",
        "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6 c1g5 f8e7 e2e3 e8g8",
        "d2d4 d7d5 g1f3 g8f6 c1f4 e7e6 e2e3 f8d6",
        "d2d4 g8f6 c2c4 g7g6 b1c3 f8g7 e2e4 d7d6 g1f3 e8g8",
        "c2c4 e7e5 b1c3 g8f6 g2g3 d7d5 c4d5 f6d5",
        "g1f3 d7d5 d2d4 g8f6 c2c4 e7e6 b1c3 f8e7",
        "e2e4 c7c5 g1f3 b8c6 d2d4 c5d4 f3d4 g7g6",
    )
    choices: dict[int, list[chess.Move]] = {}
    for line in lines:
        board = chess.Board()
        for text in line.split():
            move = chess.Move.from_uci(text)
            if move not in board.legal_moves:
                break
            key = _key(board)
            if move not in choices.setdefault(key, []):
                choices[key].append(move)
            board.push(move)
    return {key: tuple(moves) for key, moves in choices.items()}


OPENING_BOOK = _build_opening_book()
BOOK_RNG = random.Random(time.time_ns())


def _time_budget(board: chess.Board, time_left_ms: int) -> float:
    remaining = max(0.001, time_left_ms / 1000.0)
    if remaining < 0.25:
        return max(0.001, remaining * 0.08)
    if remaining < 2.0:
        return min(0.10, remaining * 0.07)
    moves_to_go = max(14, 42 - board.fullmove_number)
    budget = remaining / moves_to_go + 0.08  # cautiously use part of the rated increment
    budget = min(budget, remaining * 0.10, 4.5)
    reserve = min(0.10, remaining * 0.08)
    return max(0.005, min(budget, remaining - reserve))


def _trim_tables() -> None:
    if len(TT) > TT_LIMIT:
        stale = [key for key, entry in TT.items() if entry[4] < TT_GENERATION - 1]
        for key in stale:
            TT.pop(key, None)
        if len(TT) > TT_LIMIT:
            shallow = sorted(TT, key=lambda key: (TT[key][0], TT[key][4]))
            for key in shallow[: len(TT) - TT_LIMIT]:
                TT.pop(key, None)
    if len(HISTORY) > 20_000:
        for key in list(HISTORY):
            HISTORY[key] //= 2
    if len(EVAL_CACHE) > 180_000:
        EVAL_CACHE.clear()


def get_move(fen: str, time_left_ms: int) -> str:
    """Return a legal UCI move for the supplied position."""
    global _deadline, _nodes, _completed_depth, TT_GENERATION

    started = time.perf_counter()
    board = chess.Board(fen)
    legal = list(board.legal_moves)
    if not legal:
        return "0000"
    if len(legal) == 1:
        return legal[0].uci()

    root_key = _key(board)
    POSITION_COUNTS[root_key] = POSITION_COUNTS.get(root_key, 0) + 1
    TT_GENERATION += 1
    _trim_tables()

    book_moves = OPENING_BOOK.get(root_key)
    if book_moves:
        move = BOOK_RNG.choice(book_moves)
        if move in board.legal_moves:
            print(f"book move={move.uci()} learned={LEARNED_MODEL_ACTIVE}")
            return move.uci()

    legal.sort(key=lambda move: _move_score(board, move, None, 0), reverse=True)
    best_move = legal[0]
    if time_left_ms <= 30:
        return best_move.uci()

    _nodes = 0
    _completed_depth = 0
    _deadline = started + _time_budget(board, time_left_ms)
    previous_score = 0

    try:
        for depth in range(1, 64):
            if depth == 1:
                score, candidate = _root_search(board, depth, best_move)
            else:
                window = 40
                while True:
                    alpha = max(-INF, previous_score - window)
                    beta = min(INF, previous_score + window)
                    score, candidate = _root_search(board, depth, best_move, alpha, beta)
                    if score <= alpha:
                        window *= 2
                    elif score >= beta:
                        window *= 2
                    else:
                        break
                    if window >= 800:
                        score, candidate = _root_search(board, depth, best_move)
                        break
            best_move = candidate
            previous_score = score
            _completed_depth = depth
            if abs(score) >= MATE - MAX_PLY:
                break
    except SearchTimeout:
        pass

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    print(
        f"move={best_move.uci()} depth={_completed_depth} nodes={_nodes} "
        f"time={elapsed_ms}ms score={previous_score} learned={LEARNED_MODEL_ACTIVE}"
    )
    return best_move.uci()
