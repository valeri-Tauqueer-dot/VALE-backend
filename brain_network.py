"""VALE Brain Network: peer-to-peer communication and shared task state."""
from __future__ import annotations
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from brain_state import VALEBrainState
from vale_connector import VALEConnector

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class BrainNetwork:
    NETWORK_VERSION = "1.0"
    def __init__(self, connector: VALEConnector, max_brain_rounds: int = 3, max_events_per_task: int = 500):
        self.connector = connector
        self.brains: Dict[str, Any] = {}
        self.tasks: Dict[str, VALEBrainState] = {}
        self.max_brain_rounds = max(1, int(max_brain_rounds))
        self.max_events_per_task = max(50, int(max_events_per_task))
        self._lock = RLock()

    def register(self, brain: Any) -> Any:
        if brain is None:
            raise ValueError("Cannot register an empty brain.")
        name = str(getattr(brain, "brain_name", "") or getattr(brain, "name", "")).strip().upper()
        if not name:
            raise ValueError("Brain must expose brain_name or name.")
        with self._lock:
            if name in self.brains:
                raise ValueError(f"Brain '{name}' is already registered.")
            self.brains[name] = brain
            attach = getattr(brain, "attach_network", None)
            if callable(attach):
                attach(self)
        return brain

    def unregister(self, brain_name: str) -> bool:
        with self._lock:
            return self.brains.pop(brain_name.strip().upper(), None) is not None

    def get_brain(self, brain_name: str) -> Optional[Any]:
        return self.brains.get(brain_name.strip().upper())

    def brain_names(self) -> List[str]:
        with self._lock:
            return list(self.brains.keys())

    def create_task(self, user_message: str, conversation: Optional[List[Dict[str, Any]]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> VALEBrainState:
        state = VALEBrainState(user_message=user_message, conversation=conversation, metadata=metadata)
        state.set("network_version", self.NETWORK_VERSION)
        state.set("brains", self.brain_names())
        state.event("task_created", "VALE_NETWORK", payload={"task_id": state.task_id})
        with self._lock:
            self.tasks[state.task_id] = state
        return state

    def get_task(self, task_id: str) -> Optional[VALEBrainState]:
        with self._lock:
            return self.tasks.get(task_id)

    def close_task(self, task_id: str) -> Optional[VALEBrainState]:
        with self._lock:
            return self.tasks.pop(task_id, None)

    def ask(self, source_brain: str, target_brain: str, message: str, state: VALEBrainState,
            payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        source, target = source_brain.strip().upper(), target_brain.strip().upper()
        target_instance = self.get_brain(target)
        if target_instance is None:
            state.event("brain_message_failed", source, target, {"reason": "target_brain_not_found", "message": message})
            return {"success": False, "source": source, "target": target, "error": f"Brain '{target}' is not registered."}
        state.event("brain_message", source, target, {"message": message, "data": payload or {}})
        receive = getattr(target_instance, "receive_message", None)
        if not callable(receive):
            return {"success": False, "source": source, "target": target, "error": f"Brain '{target}' does not implement receive_message()."}
        try:
            result = receive(message=message, state=state, source_brain=source, payload=payload or {})
            state.event("brain_message_completed", target, source, {"message": message})
            return {"success": True, "source": source, "target": target, "result": result}
        except Exception as exc:
            state.event("brain_message_error", target, source, {"error": str(exc)})
            return {"success": False, "source": source, "target": target, "error": str(exc)}

    def broadcast(self, source_brain: str, message: str, state: VALEBrainState,
                  payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        source = source_brain.strip().upper()
        return {name: self.ask(source, name, message, state, payload)
                for name in self.brain_names() if name != source}

    def run_brain(self, brain_name: str, state: VALEBrainState) -> Dict[str, Any]:
        name = brain_name.strip().upper()
        brain = self.get_brain(name)
        if brain is None:
            return {"success": False, "brain": name, "error": "Brain not registered."}
        think = getattr(brain, "think", None)
        if not callable(think):
            return {"success": False, "brain": name, "error": "Brain does not implement think()."}
        state.event("brain_think_started", name)
        try:
            result = think(state)
            state.event("brain_think_completed", name)
            return {"success": True, "brain": name, "result": result}
        except Exception as exc:
            state.event("brain_think_error", name, payload={"error": str(exc)})
            return {"success": False, "brain": name, "error": str(exc)}

    def run_all(self, state: VALEBrainState) -> Dict[str, Any]:
        return {name: self.run_brain(name, state) for name in self.brain_names()}

    def process(self, user_message: str, conversation: Optional[List[Dict[str, Any]]] = None,
                metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        state = self.create_task(user_message, conversation, metadata)
        state.add_message("user", user_message)
        state.set("round", 1)
        results = self.run_all(state)
        state.event("network_round_completed", "VALE_NETWORK", payload={"round": 1, "brain_count": len(self.brains)})
        return {"task_id": state.task_id, "success": True, "results": results, "state": state}

    def status(self) -> Dict[str, Any]:
        return {"network": "VALE Brain Network", "version": self.NETWORK_VERSION, "status": "ONLINE",
                "brain_count": len(self.brains), "brains": self.brain_names(), "active_tasks": len(self.tasks),
                "brain_to_brain_communication": True, "shared_state": True, "shared_connector": True,
                "connector": self.connector.status(), "checked": utc_now()}
