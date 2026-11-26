"""Local ODMO integration regression. Run against an isolated demo server only.

Usage: python tests/wzvizinho_local_flow.py --host 192.168.100.10 --world WzVizinho
Uses a normal login; enter the disposable demo password when prompted.
No client executable, public server, or administrative credentials are used.
"""
import argparse
import getpass
import ipaddress
import socket
import struct

MAGIC = 0x2B4D1A3C
LOCAL = tuple(map(ipaddress.ip_network, ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8")))

def require(condition, message):
    if not condition:
        raise ValueError(message)

def local_host(value):
    address = ipaddress.IPv4Address(value)
    require(any(address in subnet for subnet in LOCAL), "Use a private IPv4 address or loopback")
    return str(address)

def exact(sock, length):
    result = bytearray()
    while len(result) < length:
        part = sock.recv(length - len(result))
        if not part:
            raise EOFError("Connection closed")
        result.extend(part)
    return bytes(result)

def frame(op, payload=b""):
    size = len(payload) + 10
    return struct.pack("<Ih", size, op) + payload + struct.pack("<I", size ^ MAGIC)

def expect(sock, op, allowed=()):
    for _ in range(16):
        size, = struct.unpack("<I", exact(sock, 4))
        require(10 <= size <= 65535, "Invalid frame length")
        data = exact(sock, size - 4)
        require(struct.unpack_from("<I", data, len(data)-4)[0] == size ^ MAGIC, "Bad frame checksum")
        actual, = struct.unpack_from("<h", data)
        if actual == op:
            return data[2:-4]
        require(actual in allowed, f"Unexpected opcode {actual}; expected {op}")
    raise ValueError("Expected response not received")

def text(value):
    data = value.encode("utf-8")
    return struct.pack("<H", len(data)) + data

def read_text(data, pos):
    length, = struct.unpack_from("<H", data, pos)
    end = pos + 2 + length
    require(end <= len(data), "Incomplete text")
    return data[pos+2:end].decode("utf-8"), end

def connect(host, port):
    sock = socket.create_connection((host, port), timeout=20)
    try:
        require(len(expect(sock, -1)) == 12, "Invalid handshake")
        sock.sendall(frame(-1, bytes([1])))
        require(len(expect(sock, -2)) == 6, "Invalid confirmation")
        return sock
    except Exception:
        sock.close()
        raise

def run(args, password):
    host = local_host(args.host)
    with connect(host, args.account_port) as account:
        payload = struct.pack("<I", 0) + text("") + text(args.username) + text(password) + text("") + text("") + struct.pack("<I", 0) + text("") + text("")
        account.sendall(frame(3301, payload))
        response = expect(account, 3301)
        require(len(response) == 5 and response[:4] == bytes(4), "Login refused")
        require(response[4] == 1, "Secondary authentication required; stopped")
        print("PASS: account login")
        account.sendall(frame(1701))
        data = expect(account, 1701, (10003,))
        require(bool(data), "Empty world list")
        pos, worlds = 1, {}
        for _ in range(data[0]):
            sid, = struct.unpack_from("<I", data, pos)
            name, pos = read_text(data, pos+4)
            require(pos + 6 <= len(data), "Incomplete world record")
            pos += 6
            worlds[sid] = name
        require(worlds.get(args.world_id) == args.world, "Expected world not found")
        account.sendall(frame(1702, struct.pack("<i", args.world_id)))
        data = expect(account, 901, (10003,))
        account_id, ticket = struct.unpack_from("<II", data)
        target, pos = read_text(data, 8)
        port, = struct.unpack_from("<I", data, pos)
        require(target == host and port == args.character_port, "Unexpected character target; stopped")
        auth = struct.pack("<III", 0, account_id, ticket)
        with connect(host, port) as character:
            character.sendall(frame(1706, auth))
            data = expect(character, 1301)
            require(len(data) >= 8 and data[0] > 0, "No demo character")
            slot, = struct.unpack_from("<I", data, 4)
            print("PASS: character list")
            character.sendall(frame(1305, struct.pack("<i", slot)))
            data = expect(character, 1308)
            target, pos = read_text(data, 0)
            port, map_id = struct.unpack_from("<ii", data, pos)
            require(target == host and port == args.game_port, "Unexpected game target; stopped")
            with connect(host, port) as game:
                game.sendall(frame(1706, auth))
                data = expect(game, 1003)
                require(bool(data), "Empty world bootstrap")
                print(f"PASS: world bootstrap, map {map_id}, {len(data)} bytes")
    print("PASS: local server flow. Rendering and gameplay not tested.")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--account-port", type=int, default=7000)
    parser.add_argument("--character-port", type=int, default=7001)
    parser.add_argument("--game-port", type=int, default=7002)
    parser.add_argument("--username", default="ODMO")
    parser.add_argument("--world-id", type=int, default=1)
    parser.add_argument("--world", default="WzVizinho")
    args = parser.parse_args()
    try:
        local_host(args.host)
        require(all(1 <= p <= 65535 for p in (args.account_port, args.character_port, args.game_port)), "Invalid port")
        run(args, getpass.getpass("Disposable demo password: "))
        return 0
    except (OSError, EOFError, ValueError, struct.error) as error:
        print(f"FAIL: {error}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
