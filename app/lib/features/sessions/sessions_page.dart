import 'package:flutter/material.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/w_button.dart';
import '../../core/widgets/w_card.dart';

class SessionItem {
  final String id;
  final String otherPartyName;
  final String college;
  final String intent;
  final String? notes;
  final String status; // pending, accepted, scheduled, completed, rated, declined, no_show
  final String? declineReason;
  final String? meetingLink;
  final String? confirmedSlot;
  final List<String> proposedSlots;
  final bool rated;

  const SessionItem({
    required this.id,
    required this.otherPartyName,
    required this.college,
    required this.intent,
    this.notes,
    required this.status,
    this.declineReason,
    this.meetingLink,
    this.confirmedSlot,
    this.proposedSlots = const [],
    this.rated = false,
  });
}

class ChatMessage {
  final String sender;
  final String text;
  final bool isMe;
  final String time;
  final String? safetyWarning;

  const ChatMessage({
    required this.sender,
    required this.text,
    required this.isMe,
    required this.time,
    this.safetyWarning,
  });
}

class SessionsPage extends StatefulWidget {
  const SessionsPage({super.key});

  @override
  State<SessionsPage> createState() => _SessionsPageState();
}

class _SessionsPageState extends State<SessionsPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Sample real data showing lifecycle states
  final List<SessionItem> _sessions = [
    const SessionItem(
      id: "req-101",
      otherPartyName: "Priya Sharma (Staff Eng @ Google)",
      college: "VIPS-TC Verified Alumni",
      intent: "System design deep dive & mock interview",
      notes: "Focusing on large-scale distributed queues and rate limiting.",
      status: "scheduled",
      confirmedSlot: "Tomorrow, 8:00 PM - 8:45 PM",
      meetingLink: "https://meet.jit.si/warmpath-req-101",
    ),
    const SessionItem(
      id: "req-102",
      otherPartyName: "Rohan Verma (SWE @ Microsoft)",
      college: "DTU Verified Alumni",
      intent: "Resume review and transition to backend engineering",
      status: "accepted",
      proposedSlots: ["Friday, 6:00 PM", "Saturday, 11:00 AM"],
    ),
    const SessionItem(
      id: "req-103",
      otherPartyName: "Ananya Roy (Product Manager @ Uber)",
      college: "IIT Delhi Verified Alumni",
      intent: "Product design case review",
      status: "pending",
      notes: "Looking for feedback on student project architecture.",
    ),
    const SessionItem(
      id: "req-104",
      otherPartyName: "Karan Mehta (Tech Lead @ Atlassian)",
      college: "NSUT Verified Alumni",
      intent: "Career roadmap & negotiation prep",
      status: "completed",
      rated: false,
    ),
    const SessionItem(
      id: "req-105",
      otherPartyName: "Aditi Rao (Senior SWE @ Amazon)",
      college: "IIIT Hyderabad Verified Alumni",
      intent: "Distributed databases and caching strategies",
      status: "declined",
      declineReason: "Currently on-call this week with production releases. Please request next week!",
    ),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'scheduled':
        return AppColors.deepIndigo;
      case 'accepted':
        return AppColors.teal;
      case 'pending':
        return AppColors.amber;
      case 'completed':
      case 'rated':
        return AppColors.successGreen;
      case 'declined':
        return AppColors.slate;
      case 'no_show':
        return Colors.red.shade700;
      default:
        return AppColors.slate;
    }
  }

  String _getStatusLabel(String status, bool rated) {
    switch (status.toLowerCase()) {
      case 'scheduled':
        return 'Scheduled - Meeting Ready';
      case 'accepted':
        return 'Accepted - Slot Pending';
      case 'pending':
        return 'Pending Giver Response';
      case 'completed':
        return rated ? 'Completed & Rated' : 'Completed - Rate Now';
      case 'declined':
        return 'Declined';
      case 'no_show':
        return 'No-Show (Refunded)';
      default:
        return status.toUpperCase();
    }
  }

  void _openChat(SessionItem session) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _ChatBottomSheet(session: session),
    );
  }

  void _showRatingDialog(SessionItem session) {
    int rating = 5;
    final commentCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          shape: const RoundedRectangleBorder(borderRadius: AppRadii.card),
          title: const Text('Rate Mentorship Session', style: TextStyle(fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('How was your session with ${session.otherPartyName}?'),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (index) {
                  return IconButton(
                    icon: Icon(
                      index < rating ? Icons.star : Icons.star_border,
                      color: AppColors.amber,
                      size: 32,
                    ),
                    onPressed: () => setState(() => rating = index + 1),
                  );
                }),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: commentCtrl,
                decoration: const InputDecoration(
                  hintText: 'Share feedback on preparation and clarity...',
                  border: OutlineInputBorder(borderRadius: AppRadii.button),
                ),
                maxLines: 3,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primaryAction,
                foregroundColor: AppColors.white,
                shape: const RoundedRectangleBorder(borderRadius: AppRadii.button),
              ),
              onPressed: () {
                Navigator.pop(ctx);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Rating submitted! Trust score updated.'),
                    backgroundColor: AppColors.successGreen,
                  ),
                );
              },
              child: const Text('Submit Rating'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final activeSessions = _sessions.where((s) => ['pending', 'accepted', 'scheduled'].contains(s.status)).toList();
    final pastSessions = _sessions.where((s) => ['completed', 'rated', 'declined', 'no_show'].contains(s.status)).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mentorship Sessions', style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.textDark)),
        backgroundColor: AppColors.white,
        elevation: 1,
        bottom: TabBar(
          controller: _tabController,
          labelColor: AppColors.deepIndigo,
          indicatorColor: AppColors.primaryAction,
          indicatorWeight: 3,
          tabs: [
            Tab(text: 'Active (${activeSessions.length})'),
            Tab(text: 'History (${pastSessions.length})'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildSessionList(activeSessions),
          _buildSessionList(pastSessions),
        ],
      ),
    );
  }

  Widget _buildSessionList(List<SessionItem> items) {
    if (items.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32.0),
          child: Text('No sessions in this category.', style: TextStyle(color: AppColors.slate, fontSize: 16)),
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16.0),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 14),
      itemBuilder: (ctx, index) {
        final session = items[index];
        final statusColor = _getStatusColor(session.status);

        return WCard(
          padding: const EdgeInsets.all(18.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row: Status Pill & Role Privacy notice
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.12),
                      borderRadius: AppRadii.badge,
                      border: Border.all(color: statusColor.withOpacity(0.4)),
                    ),
                    child: Text(
                      _getStatusLabel(session.status, session.rated),
                      style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                  ),
                  const Row(
                    children: [
                      Icon(Icons.shield_outlined, size: 14, color: AppColors.slate),
                      SizedBox(width: 4),
                      Text('Contact masked', style: TextStyle(fontSize: 12, color: AppColors.slate)),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Party & College
              Text(session.otherPartyName, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppColors.textDark)),
              const SizedBox(height: 2),
              Text(session.college, style: const TextStyle(fontSize: 13, color: AppColors.slate)),
              const SizedBox(height: 10),

              // Intent
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: AppRadii.badge,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Intent / Agenda:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.slate)),
                    const SizedBox(height: 2),
                    Text(session.intent, style: const TextStyle(fontSize: 14, color: AppColors.textDark)),
                    if (session.notes != null) ...[
                      const SizedBox(height: 4),
                      Text('Note: ${session.notes}', style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: AppColors.slate)),
                    ],
                  ],
                ),
              ),

              // Status Specific Sections
              if (session.status == 'scheduled' && session.meetingLink != null) ...[
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.teal.withOpacity(0.1),
                    borderRadius: AppRadii.badge,
                    border: Border.all(color: AppColors.teal.withOpacity(0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.videocam, color: AppColors.teal),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(session.confirmedSlot ?? 'Scheduled Session', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.textDark)),
                            const Text('Meeting room ready via Jitsi Meet', style: TextStyle(fontSize: 11, color: AppColors.slate)),
                          ],
                        ),
                      ),
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.teal,
                          foregroundColor: AppColors.white,
                          shape: const RoundedRectangleBorder(borderRadius: AppRadii.badge),
                        ),
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Opening video room: ${session.meetingLink}')),
                          );
                        },
                        icon: const Icon(Icons.call, size: 16),
                        label: const Text('Join Call'),
                      ),
                    ],
                  ),
                ),
              ],

              if (session.status == 'declined' && session.declineReason != null) ...[
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: AppRadii.badge,
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.info_outline, size: 16, color: Colors.red.shade700),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Decline Reason: ${session.declineReason}',
                          style: TextStyle(fontSize: 12, color: Colors.red.shade800),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              if (session.status == 'accepted' && session.proposedSlots.isNotEmpty) ...[
                const SizedBox(height: 12),
                const Text('Proposed Slots from Giver:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.slate)),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  children: session.proposedSlots.map((slot) {
                    return ActionChip(
                      backgroundColor: AppColors.white,
                      side: const BorderSide(color: AppColors.deepIndigo),
                      label: Text(slot, style: const TextStyle(fontSize: 12, color: AppColors.deepIndigo, fontWeight: FontWeight.w600)),
                      avatar: const Icon(Icons.schedule, size: 14, color: AppColors.deepIndigo),
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Slot "$slot" confirmed! Calendar event created.')),
                        );
                      },
                    );
                  }).toList(),
                ),
              ],

              const SizedBox(height: 14),

              // Action buttons row: In-App Chat & Rate
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.deepIndigo,
                      side: const BorderSide(color: AppColors.deepIndigo),
                      shape: const RoundedRectangleBorder(borderRadius: AppRadii.badge),
                    ),
                    onPressed: () => _openChat(session),
                    icon: const Icon(Icons.chat_bubble_outline, size: 16),
                    label: const Text('In-App Chat'),
                  ),
                  if (session.status == 'completed' && !session.rated) ...[
                    const SizedBox(width: 8),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primaryAction,
                        foregroundColor: AppColors.white,
                        shape: const RoundedRectangleBorder(borderRadius: AppRadii.badge),
                      ),
                      onPressed: () => _showRatingDialog(session),
                      icon: const Icon(Icons.star, size: 16),
                      label: const Text('Rate Session'),
                    ),
                  ],
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ChatBottomSheet extends StatefulWidget {
  final SessionItem session;
  const _ChatBottomSheet({required this.session});

  @override
  State<_ChatBottomSheet> createState() => _ChatBottomSheetState();
}

class _ChatBottomSheetState extends State<_ChatBottomSheet> {
  final TextEditingController _msgCtrl = TextEditingController();
  final List<ChatMessage> _messages = [
    const ChatMessage(
      sender: 'System',
      text: 'Request thread initiated. Direct contact details (phone, email, payments) are strictly blocked to protect student & giver privacy.',
      isMe: false,
      time: '10:00 AM',
    ),
    const ChatMessage(
      sender: 'Student',
      text: 'Hi! Looking forward to reviewing the system design architecture.',
      isMe: true,
      time: '10:02 AM',
    ),
    const ChatMessage(
      sender: 'Giver',
      text: 'Great to connect! Please upload your draft diagram or agenda here before our call.',
      isMe: false,
      time: '10:05 AM',
    ),
  ];

  void _sendMessage() {
    final text = _msgCtrl.text.trim();
    if (text.isEmpty) return;

    // Client-side scam preview detection (matching backend SafetyPort)
    final phoneRegex = RegExp(r'(?:\+?91[\-\s]?)?[6-9]\d{9}|\b\d{10}\b');
    final paymentRegex = RegExp(r'upi|gpay|phonepe|paytm|send money|transfer money', caseSensitive: false);

    if (phoneRegex.hasMatch(text) || paymentRegex.hasMatch(text)) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: const RoundedRectangleBorder(borderRadius: AppRadii.card),
          title: const Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: Colors.red),
              SizedBox(width: 8),
              Text('Message Blocked', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
            ],
          ),
          content: const Text(
            'Safety Alert: Phone numbers, personal contact details, and payment requests are prohibited. '
            'This violation has been logged. Repeated violations reduce trust score.',
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Understood')),
          ],
        ),
      );
      return;
    }

    setState(() {
      _messages.add(
        ChatMessage(
          sender: 'Me',
          text: text,
          isMe: true,
          time: 'Now',
        ),
      );
      _msgCtrl.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      decoration: const BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        children: [
          // Drag handle
          Container(
            margin: const EdgeInsets.only(top: 8),
            width: 40,
            height: 4,
            decoration: BoxDecoration(color: AppColors.slate.withOpacity(0.3), borderRadius: BorderRadius.circular(2)),
          ),
          // Sheet Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Chat with ${widget.session.otherPartyName}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      Text(widget.session.intent, style: const TextStyle(fontSize: 12, color: AppColors.slate), maxLines: 1, overflow: TextOverflow.ellipsis),
                    ],
                  ),
                ),
                IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context)),
              ],
            ),
          ),
          // Safety Banner
          Container(
            width: double.infinity,
            margin: const EdgeInsets.symmetric(horizontal: 16),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.amber.shade50,
              borderRadius: AppRadii.badge,
              border: Border.all(color: Colors.amber.shade200),
            ),
            child: Row(
              children: [
                Icon(Icons.security, size: 18, color: Colors.amber.shade900),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Scam Detection Active: Phone numbers, emails, social handles, and off-platform payments are automatically blocked.',
                    style: TextStyle(fontSize: 11, color: Colors.amber.shade900, fontWeight: FontWeight.w500),
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 20),
          // Message list
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _messages.length,
              itemBuilder: (ctx, index) {
                final m = _messages[index];
                return Align(
                  alignment: m.isMe ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                    decoration: BoxDecoration(
                      color: m.isMe ? AppColors.deepIndigo : AppColors.surface,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          m.text,
                          style: TextStyle(color: m.isMe ? AppColors.white : AppColors.textDark, fontSize: 14),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          m.time,
                          style: TextStyle(color: m.isMe ? AppColors.white.withOpacity(0.7) : AppColors.slate, fontSize: 10),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          // Input bar
          SafeArea(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.white,
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4, offset: const Offset(0, -2)),
                ],
              ),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _msgCtrl,
                      decoration: const InputDecoration(
                        hintText: 'Type a message (contact details blocked)...',
                        border: InputBorder.none,
                      ),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send, color: AppColors.primaryAction),
                    onPressed: _sendMessage,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
