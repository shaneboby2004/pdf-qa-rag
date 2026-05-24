import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';

interface Message {
  role: 'user' | 'bot';
  text: string;
  sources?: { page: string | number; preview: string }[];
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class AppComponent {

  selectedFile: File | null = null;
  collectionName: string = '';
  uploadedFilename: string = '';
  uploading = false;
  indexing = false;
  uploadError = '';

  messages: Message[] = [];
  question = '';
  loading = false;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      this.selectedFile = input.files[0];
      this.uploadError = '';
    }
  }

  uploadFile() {
    if (!this.selectedFile) return;
    this.uploading = true;
    this.indexing = false;
    this.uploadError = '';
    this.collectionName = '';
    this.messages = [];

    this.api.uploadPdf(this.selectedFile).subscribe({
      next: (res) => {
        this.uploading = false;
        this.uploadedFilename = res.filename;

        if (res.status === 'ready') {
          this.collectionName = res.collection_name;
          this.messages.push({
            role: 'bot',
            text: `✅ ${res.filename} is ready${res.cached ? ' (cached)' : ''}. Ask me anything about it!`
          });
          this.cdr.detectChanges();
          return;
        }

        this.indexing = true;
        this.cdr.detectChanges();

        this.api.pollStatus(res.collection_name).subscribe({
          next: (statusRes: any) => {
            if (statusRes.status === 'ready') {
              this.collectionName = res.collection_name;
              this.indexing = false;
              this.messages.push({
                role: 'bot',
                text: `✅ ${res.filename} indexed and ready. Ask me anything about it!`
              });
              this.cdr.detectChanges();
            } else if (statusRes.status?.startsWith('error')) {
              this.indexing = false;
              this.uploadError = 'Indexing failed. Please try again.';
              this.cdr.detectChanges();
            }
          },
          error: () => {
            this.indexing = false;
            this.uploadError = 'Could not check indexing status.';
            this.cdr.detectChanges();
          }
        });
      },
      error: (err) => {
        this.uploadError = err.error?.detail || 'Upload failed. Is the backend running?';
        this.uploading = false;
        this.cdr.detectChanges();
      }
    });
  }

  sendQuestion() {
    const q = this.question.trim();
    if (!q || !this.collectionName || this.loading) return;

    this.messages.push({ role: 'user', text: q });
    this.question = '';
    this.loading = true;

    const botMsgIndex = this.messages.length;
    this.messages.push({ role: 'bot', text: '', sources: [] });

    this.api.queryStream(
      q,
      this.collectionName,
      (chunk: string) => {
        this.messages[botMsgIndex].text += chunk;
        this.scrollToBottom();
        this.cdr.detectChanges();
      },
      (sources: any[]) => {
        this.messages[botMsgIndex].sources = sources;
        this.cdr.detectChanges();
      },
      () => {
        this.loading = false;
        this.cdr.detectChanges();
      },
      () => {
        this.messages[botMsgIndex].text = '❌ Something went wrong. Please try again.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    );
  }

  onEnter(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendQuestion();
    }
  }

  scrollToBottom() {
    setTimeout(() => {
      const el = document.getElementById('chat-window');
      if (el) el.scrollTop = el.scrollHeight;
    }, 100);
  }
}