from events import EventKind, parse_line


def _line(msg: str, time: str = "14:23:05", level: str = "INFO", thread: str = "Server thread") -> str:
    return f"[{time}] [{thread}/{level}]: {msg}\n"


def test_death_slain_by_mob():
    ev = parse_line(_line("Player1 was slain by Piglin"))
    assert ev.kind == EventKind.DEATH
    assert ev.player == "Player1"
    assert ev.time_str == "14:23:05"
    assert ev.text == "Player1 was slain by Piglin"


def test_death_fell_from_a_high_place():
    ev = parse_line(_line("Player2 fell from a high place"))
    assert ev.kind == EventKind.DEATH
    assert ev.player == "Player2"


def test_death_hit_the_ground_too_hard():
    ev = parse_line(_line("Player3 hit the ground too hard"))
    assert ev.kind == EventKind.DEATH
    assert ev.player == "Player3"


def test_death_drowned():
    ev = parse_line(_line("Player4 drowned"))
    assert ev.kind == EventKind.DEATH
    assert ev.player == "Player4"


def test_death_blew_up():
    ev = parse_line(_line("Player5 blew up"))
    assert ev.kind == EventKind.DEATH
    assert ev.player == "Player5"


def test_death_world_border():
    ev = parse_line(_line("Player6 left the confines of this world"))
    assert ev.kind == EventKind.DEATH
    assert ev.player == "Player6"


def test_join():
    ev = parse_line(_line("Steve joined the game"))
    assert ev.kind == EventKind.JOIN
    assert ev.player == "Steve"
    assert ev.text == "Steve joined the game"


def test_leave():
    ev = parse_line(_line("Steve left the game"))
    assert ev.kind == EventKind.LEAVE
    assert ev.player == "Steve"


def test_advancement_made():
    ev = parse_line(_line("Steve has made the advancement [Stone Age]"))
    assert ev.kind == EventKind.ADVANCEMENT
    assert ev.player == "Steve"
    assert ev.text == "Steve has made the advancement [Stone Age]"


def test_advancement_goal():
    ev = parse_line(_line("Steve has reached the goal [Bee Our Guest]"))
    assert ev.kind == EventKind.ADVANCEMENT
    assert ev.player == "Steve"


def test_advancement_challenge():
    ev = parse_line(_line("Steve has completed the challenge [Uneasy Alliance]"))
    assert ev.kind == EventKind.ADVANCEMENT
    assert ev.player == "Steve"


def test_server_start():
    ev = parse_line(_line('Done (34.567s)! For help, type "help"'))
    assert ev.kind == EventKind.SERVER_START
    assert ev.player is None


def test_server_stop():
    ev = parse_line(_line("Stopping the server"))
    assert ev.kind == EventKind.SERVER_STOP
    assert ev.player is None


def test_named_entity_diagnostic_dump_is_filtered():
    msg = "Named entity Wolf['Rex'/123, uuid=deadbeef-...] died: Rex was slain by Zombie"
    assert parse_line(_line(msg)) is None


def test_console_no_entity_was_found_is_not_filtered_here():
    # "No entity was found" is a console response to a failed command, not a real player
    # death, but events.py has no notion of "who is currently online" — that filtering is
    # the caller's job (SessionTracker.is_online), so parse_line intentionally still
    # produces a DEATH event here (with a bogus player).
    ev = parse_line(_line("No entity was found"))
    assert ev.kind == EventKind.DEATH
    assert ev.player == "No"


def test_player_chat_is_not_an_event():
    assert parse_line(_line("<Steve> hello, was anyone here?")) is None


def test_cyrillic_nickname_join():
    ev = parse_line(_line("Клюква joined the game"))
    assert ev.kind == EventKind.JOIN
    assert ev.player == "Клюква"


def test_cyrillic_nickname_death():
    ev = parse_line(_line("Клюква was slain by Zombie"))
    assert ev.kind == EventKind.DEATH
    assert ev.player == "Клюква"


def test_non_info_level_is_ignored():
    assert parse_line(_line("Can't keep up! Is the server overloaded?", level="WARN")) is None


def test_unmatched_line_is_none():
    assert parse_line(_line("Preparing spawn area: 50%")) is None


def test_malformed_line_without_log_prefix_is_none():
    assert parse_line("just some text with no timestamp prefix\n") is None


def test_line_without_trailing_newline():
    ev = parse_line("[14:23:05] [Server thread/INFO]: Steve joined the game")
    assert ev.kind == EventKind.JOIN


def test_thread_name_with_spaces_and_hash():
    ev = parse_line(_line("Steve joined the game", thread="User Authenticator #1"))
    assert ev.kind == EventKind.JOIN
