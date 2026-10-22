# Contributing to Neuron

Thank you for your interest in contributing to **Neuron** — a brain-inspired modular AI framework focused on observability, fault tolerance, and cognitive integrity.

## How to Contribute

### Getting Started

1. **Fork the repository**
2. **Clone your fork**: `git clone https://github.com/yourusername/neuron.git`
3. **Create a new branch**: `git checkout -b feature/your-feature-name`
4. **Install for development**: `pip install -e ".[dev]"`
5. **Make your changes**
6. **Test your changes**: `python -m pytest tests agents src/neurons` (CI also runs each sub-project's tests and `flake8 . --select=E9,F63,F7,F82`)
7. **Commit your changes**: `git commit -m "Add your descriptive commit message"`
8. **Push to your fork**: `git push origin feature/your-feature-name`
9. **Open a Pull Request**

### Types of Contributions

We welcome:

- **Bug fixes and improvements**
- **New features and modules**
- **Documentation improvements**
- **Test cases and benchmarks**
- **Performance optimizations**

### Code Standards

- Python 3.10+
- Follow PEP8 formatting with Black: `black --line-length=88`
- Include type annotations
- Add docstrings for all public functions and classes
- Write tests for new features
- Update documentation as needed

### Use Case Contributions

Have a real-world edge case Neuron should support?  
Submit it to the `neuron-bench/` dataset, open a feature request, or start a [GitHub Discussion](https://github.com/ShaliniAnandaPhD/Neuron/discussions).  

We love building against real-world failure modes — your contribution could become part of the official benchmark suite.



### Repository Structure

```
src/neuron/
├── agent.py            # BaseAgent and the built-in agent types
├── synaptic_bus.py     # Message passing between agents
├── circuit_designer.py # Circuits, connections and templates
├── memory.py           # Memory systems
├── neuro_monitor.py    # Health and metrics
├── cli.py              # The `neuron` command
├── agents/             # Specialised agents (fallback, simulation)
├── core/               # Routing helpers
├── observability/      # Tracing
└── integration/        # Agent voting and reliability routing

tests/                  # Framework tests
examples/               # Runnable examples
docs/                   # Documentation
```

## Pull Request Guidelines

- **Describe your changes clearly** in the PR description
- **Reference any related issues** using `#issue-number`
- **Ensure all tests pass** before submitting
- **Keep changes focused** - one feature per PR
- **Update documentation** if you're changing APIs

## Reporting Issues

When reporting bugs or requesting features:

- **Use the issue template** if available
- **Provide clear reproduction steps** for bugs
- **Include your environment details** (Python version, OS, etc.)
- **Search existing issues** before creating new ones

👉 Please review the [NOTICE.md](NOTICE.md) file before contributing. It contains important legal and attribution guidelines.


## Legal and Licensing

### License

Neuron is licensed under a **modified MIT License with Attribution**. By contributing, you agree that your contributions will be licensed under the same terms.

### Attribution Requirements

- **You must retain all copyright, license, and attribution notices** in both code and documentation
- **You must not remove author credit** from README, LICENSE, or module headers
- **Commercial use must include visible attribution** to the original repository and author (Shalini Ananda, PhD)
- **Published research using Neuron must cite** the framework with appropriate author tags

### Contributor License Agreement

By submitting a pull request, you represent that:

- You have the right to license your contribution to us
- You agree to license your contribution under the project's license terms
- Your contribution does not violate any third-party rights

### Prohibited Uses

Do **not** use Neuron for:
- Surveillance or monitoring systems without consent
- Disinformation or misleading content generation
- Biased or discriminatory applications
- Any use that violates privacy, consent, or human dignity

## Code of Conduct

This project follows a zero-harassment policy. All contributors must:

- Be respectful and inclusive in all interactions
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different viewpoints and experiences

Harassment, discrimination, or disrespectful behavior will not be tolerated.

## Questions?

- **General questions**: Open a discussion in the GitHub Discussions tab
- **Bug reports**: Use the issue tracker
- **Security concerns**: Email the maintainers directly

---

**Project Author**: Shalini Ananda, PhD  
**Repository**: https://github.com/ShaliniAnandaPhD/Neuron

Thank you for helping make AI more resilient, transparent, and trustworthy!
