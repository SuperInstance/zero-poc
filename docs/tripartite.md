# The Tripartite

Three agents, three demarcations. Each owns exactly one side of the boundary, and none reaches across.

## 1. The human agent

Specializes in knowing the **person** — presentation, culture, judgment, conversation. It designs from the human end: sometimes just a picture, then an architecture, then a handoff. It never touches git mechanics. It thinks only about how the application should work *for this human*, the way they want it to work.

Pure front-end indirection.

## 2. The git agent

Specializes in knowing the **logic of the application**. This is what lives in this repo. It formalizes architecture into structure: code, history, docs, memory. The repo is its whole world, and it grows its understanding from the repo's perspective — the repo is everything to it.

It never touches hardware. It never performs the human relationship.

## 3. The hardware agent

Specializes in knowing how to **render the application to hardware**. Drivers are just libraries; the expert writes the right material for the destination: C or bare metal for the edge device, Python and TypeScript for the cloud deployment — whatever the application needs, where it will actually be used in service.

The last mile: same logic, different matter.

## Why three

Because the demarcations are where they are. The human, the logic, and the hardware change for different reasons, at different speeds, under different expertise. One agent spanning all three would be a monolith wearing a costume.

Decoupled, each side can be excellent at exactly one thing — and a weaker model becomes sufficient inside a narrow enough world.

## The handoffs

- **Human → git**: architecture, as issues and bottles. (This is the I2I protocol — see `docs/i2i.md`.)
- **Git → hardware**: formalized logic, as shells. (See `docs/clones.md`.)
- **Hardware → human**: the thing, running, shaped for the person.

Each handoff crosses one demarcation and no more.
